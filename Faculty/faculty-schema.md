## Proposed Schema for Faculty
## Faculty

| Column             | Type                   |
| ------------------ | ---------------------- |
| id                 | INT                    |
| full_name          | STR                    |
| first_name         | STR                    |
| last_name          | STR                    |
| middle_name        | STR                    |
| total_compensation | FLOAT                  |
| university_id      | FK → University.id     |
| position_id        | FK → Position.id       |
| field_of_study_id  | FK → Field_of_Study.id |

## University

| Column               | Type  |
| -------------------- | ----- |
| id                   | INT   |
| university_name      | STR   |
| system               | STR   |
| student_population   | INT   |
| undergrad_population | INT   |
| grad_population      | INT   |
| avg_in_state_tuition | FLOAT |
| …                    | …     |

## Position

| Column        | Type |
| ------------- | ---- |
| id            | INT  |
| position_name | STR  |
| …             | …    |

## Field of Study

| Column | Type |
| ------ | ---- |
| id     | INT  |
| name   | STR  |
