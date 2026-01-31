import os
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable

HH_MOSCOW_AREA_ID = 1
HH_SEARCH_PERIOD_DAYS = 30
SJ_MOSCOW_TOWN_ID = 4
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


def get_vacancies_hh(it_language):
    all_vacancies = []
    page = 0
    found = None
    while True:
        params = {
            'text': f'программист {it_language}',
            'area': HH_MOSCOW_AREA_ID,
            'period': HH_SEARCH_PERIOD_DAYS,
            'only_with_salary': False,
            'page': page,
            'per_page': 100
        }
        url = 'https://api.hh.ru/vacancies'
        response = requests.get(url, params=params)
        response.raise_for_status()
        response_data = response.json()
        if found is None:
            found = response_data['found']
        all_vacancies.extend(response_data['items'])
        if page >= response_data['pages'] - 1:
            break
        page += 1
    return found, all_vacancies


def get_vacancies_sj(secret_key, it_language):
    headers = {
        'X-Api-App-Id': secret_key
    }
    params = {
        'keyword': f'программист {it_language}',
        'town': SJ_MOSCOW_TOWN_ID
    }
    url = 'https://api.superjob.ru/2.0/vacancies'
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    return response_data


def predict_salary(salary_from, salary_to):
    if not salary_from and not salary_to:
        return None
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from:
        return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8


def predict_rub_salaries_hh(vacancies):
    salaries = []
    for vacancy in vacancies:
        salary = vacancy.get('salary')
        if not salary or salary.get('currency') != 'RUR':
            continue
        salary_from = salary.get("from")
        salary_to = salary.get("to")
        predicted_salary = predict_salary(salary_from, salary_to)
        if predicted_salary:
            salaries.append(predicted_salary)
    return salaries


def predict_rub_salaries_sj(vacancy):
    salary_from = vacancy.get('payment_from')
    salary_to = vacancy.get('payment_to')
    return predict_salary(salary_from, salary_to)


def get_hh_salaries(it_languages):
    hh_salaries = {}
    for it_language in it_languages:
        hh_vacancies_found, vacancies = get_vacancies_hh(it_language)
        if hh_vacancies_found < 100:
            continue
        valid_salaries_hh = predict_rub_salaries_hh(vacancies)
        if not valid_salaries_hh:
            continue
        average_salary_hh = sum(valid_salaries_hh) / len(valid_salaries_hh)
        hh_salaries[it_language] = {
            'vacancies_found': hh_vacancies_found,
            'vacancies_processed': len(valid_salaries_hh),
            'average_salary': int(average_salary_hh)
        }
    return hh_salaries


def get_sj_salaries(secret_key, it_languages):
    sj_salaries = {}
    for it_language in it_languages:
        all_vacancies = get_vacancies_sj(secret_key, it_language)
        sj_vacancies_found = all_vacancies.get('total', 0)
        vacancies = all_vacancies['objects']
        language_vacancies = []
        for vacancy in vacancies:
            profession = vacancy.get('candidat', '')
            if it_language.lower() in profession.lower():
                language_vacancies.append(vacancy)
        valid_salaries_sj = []
        for vacancy in language_vacancies:
            salary = predict_rub_salaries_sj(vacancy)
            if salary:
                valid_salaries_sj.append(salary)
        if not valid_salaries_sj:
            sj_salaries[it_language] = {
                'vacancies_found': sj_vacancies_found,
                'vacancies_processed': 0,
                'average_salary': 0
            }
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
    print(make_table(hh_stats, 'HeadHunter Moscow'))
    print()
    print(make_table(sj_stats, 'SuperJob Moscow'))


if __name__ == '__main__':
    main()
