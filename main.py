import os
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


IT_LANGUAGES = [
    'Python',
    'Java',
    'JavaScript',
    'C++',
    'C#',
    'Go',
    'PHP',
    'Ruby',
    'Swift'
]


def get_vacancies_count(it_language):
    params = {
        'text': f'программист {it_language}',
        'area': 1,
        'period': 30,
    }
    url = 'https://api.hh.ru/vacancies'
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()['found']


def get_vacancies_hh(it_language):
    all_vacancies = []
    page = 0
    while True:
        params = {
            'text': f'программист {it_language}',
            'area': 1,
            'period': 30,
            'only_with_salary': True,
            'page': page,
            'per_page': 100
        }
        url = 'https://api.hh.ru/vacancies'
        response = requests.get(url, params=params)
        response.raise_for_status()
        response_data = response.json()
        all_vacancies.extend(response_data['items'])
        if page >= response_data['pages'] - 1:
            break
        page += 1
    return all_vacancies


def get_vacancies_sj(secret_key, it_language):
    headers = {
        'X-Api-App-Id': secret_key
    }
    params = {
        'keyword': f'{it_language}',
        'town': 4
    }
    url = 'https://api.superjob.ru/2.0/vacancies'
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    return response_data


def predict_rub_salary_hh(vacancies):
    salaries = []
    for vacancy in vacancies:
        salary = vacancy.get('salary')
        if salary.get('currency') != 'RUR':
            salaries.append(None)
            continue
        salary_from = salary.get('from')
        salary_to = salary.get('to')
        if salary_from and salary_to:
            salaries.append((salary_from+salary_to)/2)
        elif salary_from:
            salaries.append(salary_from*1.2)
        elif salary_to:
            salaries.append(salary_to*0.8)
    return salaries


def predict_rub_salary_sj(vacancy):
    salary_from = vacancy.get('payment_from')
    salary_to = vacancy.get('payment_to')
    if not salary_from and not salary_to:
        return None
    if salary_from and salary_to:
        return (salary_from+salary_to)/2
    elif salary_from:
        return salary_from*1.2
    elif salary_to:
        return salary_to*0.8


def get_hh_salaries(IT_LANGUAGES):
    hh_salaries = {}
    for it_language in IT_LANGUAGES:
        hh_vacancies_found = get_vacancies_count(it_language)
        if hh_vacancies_found < 100:
            continue
        vacancies = get_vacancies_hh(it_language)
        salaries = predict_rub_salary_hh(vacancies)
        valid_salaries_hh = []
        for salary in salaries:
            if salary is not None:
                valid_salaries_hh.append(salary)
        average_salary_hh = (sum(valid_salaries_hh) / len(valid_salaries_hh))
        hh_salaries[it_language] = {
            'vacancies_found': hh_vacancies_found,
            'vacancies_processed': len(valid_salaries_hh),
            'average_salary': int(average_salary_hh)
        }
    return hh_salaries


def get_sj_salaries(secret_key, IT_LANGUAGES):
    sj_salaries = {}
    for it_language in IT_LANGUAGES:
        all_vacancies = get_vacancies_sj(secret_key, it_language)
        vacancies = all_vacancies['objects']
        language_vacancies = []
        for vacancy in vacancies:
            profession = vacancy.get('candidat', '')
            if it_language.lower() in profession.lower():
                language_vacancies.append(vacancy)
        sj_vacancies_found = len(language_vacancies)
        valid_salaries_sj = []
        for vacancy in language_vacancies:
            salary = predict_rub_salary_sj(vacancy)
            if salary is not None:
                valid_salaries_sj.append(salary)
        if not valid_salaries_sj:
            continue
        average_salary_sj = sum(valid_salaries_sj)/len(valid_salaries_sj)
        sj_salaries[it_language] = {
            'vacancies_found': sj_vacancies_found,
            'vacancies_processed': len(valid_salaries_sj),
            'average_salary': int(average_salary_sj)
        }
    return sj_salaries


def make_table(statistics, title):
    table_data = [
        (
            'Язык программирования',
            'Вакансий найдено',
            'Вакансий обработано',
            'Средняя зарплата'
        )
    ]
    for language, stats in statistics.items():
        table_data.append((
            language,
            stats['vacancies_found'],
            stats['vacancies_processed'],
            stats['average_salary']
        ))
    table = AsciiTable(table_data, title)
    return table.table


def main():
    load_dotenv()
    secret_key = os.getenv('SJ_KEY')
    hh_stats = get_hh_salaries(IT_LANGUAGES)
    sj_stats = get_sj_salaries(secret_key, IT_LANGUAGES)
    print(make_table(hh_stats, 'HeadHunter Moskow'))
    print()
    print(make_table(sj_stats, 'SuperJob Moskow'))


if __name__ == '__main__':
    main()
