***Note that I was in Chaos in 2024, so I've already done this technical assessment before. I've copied my submission from last time, with a few adjustments to the Rust code.***

> This question is relevant for **chaos backend**

# DevSoc Subcommittee Recruitment: Chaos Backend

***Complete as many questions as you can.***

## Question 1
You have been given a skeleton function `process_data` in the `data.rs` file.
Complete the parameters and body of the function so that given a JSON request of the form

```json
{
  "data": ["Hello", 1, 5, "World", "!"]
}
```

the handler returns the following JSON:
```json
{
  "string_len": 11,
  "int_sum": 6
}
```

Edit the `DataResponse` and `DataRequest` structs as you need.

## Question 2

### a)
Write (Postgres) SQL `CREATE TABLE` statements to create the following schema.
Make sure to include foreign keys for the relationships that will `CASCADE` upon deletion.
![Database Schema](db_schema.png)

**Answer box:**
```sql
CREATE TYPE question_type AS ENUM ('ShortAnswer', 'MultiSelect', 'MultiChoice');

-- I could have also required table fields such as forms.title, forms.description, questions.title, questions.question_type to be NOT NULL, but this wasn't required/defined in the problem statement.

CREATE TABLE forms (
    id INTEGER PRIMARY KEY,
    title TEXT
    description TEXT
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    form_id INTEGER NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    title TEXT,
    question_type question_type,
);

CREATE TABLE question_options (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    -- It would make more sense to not have a `question_options` item at all rather than having one with `NULL`, so require `NOT NULL`.
    option TEXT NOT NULL,
);
```

### b)
Using the above schema, write a (Postgres) SQL `SELECT` query to return all questions in the following format, given the form id `26583`:
```
   id    |   form_id   |           title             |   question_type   |     options
------------------------------------------------------------------------------------------------------------
 2       | 26583       | What is your full name?     | ShortAnswer       | [null]
 3       | 26583       | What languages do you know? | MultiSelect       | {"Rust", "JavaScript", "Python"}
 7       | 26583       | What year are you in?       | MultiChoice       | {"1", "2", "3", "4", "5+"}
```

**Answer box:**
```sql
-- Write query here
-- TODO: get all the questions, along with each question's question_options, for a specific form_id.
SELECT
    q.id,
    q.form_id,
    q.title,
    q.question_type,
    ARRAY_AGG(o.option) AS options
FROM
    questions q
-- Use left join so we also return those questions that have no options.
LEFT JOIN question_options o ON q.id = o.question_id
WHERE
    q.form_id = 26583
-- Required for aggregating question_options.
GROUP BY
    q.id, q.form_id, q.title, q.question_type
-- For ordering by questions.id.
ORDER BY
    q.id;
```
