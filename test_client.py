# -*- coding: utf-8 -*-
import json
import requests

sample = {
    "person_age": 30,
    "person_income": 60000,
    "person_emp_length": 5,
    "loan_amnt": 12000,
    "loan_int_rate": 7.5,
    "loan_percent_income": 0.2,
    "cb_person_cred_hist_length": 8,
    "person_home_ownership": "RENT",
    "loan_intent": "PERSONAL",
    "loan_grade": "B",
    "cb_person_default_on_file": "N"
}

if __name__ == "__main__":
    r = requests.get("http://127.0.0.1:5000/health")
    print("/health:", r.status_code, r.text)

    r = requests.post("http://127.0.0.1:5000/degerlendir", json=sample)
    print("/degerlendir:", r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))

    r = requests.post("http://127.0.0.1:5000/explain", json=sample)
    print("/explain:", r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
