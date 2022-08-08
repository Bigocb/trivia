import requests
import sqlite3
import string
from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap

# todo: When you use a coin don't refresh the question
# todo: Historical metrics by category (high scores, overall percentage, right, wrong)
# todo: track count of the times a question has been asked. If its over 5 don't ask anymore
# todo: Add all categories filter
# todo: BUG: Should not be able to lose on a correct answer
# todo: Make it all categories to start

app = Flask(__name__)
Bootstrap(app)
state = {
    'skips': 5,
    'coins': 0,
    'run': 0
}

connection = sqlite3.connect("aquarium.db", check_same_thread=False)
cursor = connection.cursor()


def update_state():
    return 1


def build_answer_array(questions):
    answers = []

    try:
        answer = (
            questions['correct_answer'].replace('&#039;', "'").replace('&quot;', '"').replace('&rsquo;',
                                                                                              '''''').replace(
                '&ldquo;', '"').replace('&amp;', '&'),
            (''.join(char for char in questions['correct_answer'] if char.isalnum())).lower())
        answers.append(answer)

        for i in questions['incorrect_answers']:
            answer = (
                i.replace('&#039;', "'").replace('&quot;', '"').replace('&rsquo;', '''''').replace('&ldquo;',
                                                                                                   '"').replace(
                    '&amp;', '&'), (''.join(char for char in i if char.isalnum())).lower())
            answers.append(answer)
    except Exception as error:
        cursor.execute(f"INSERT INTO exceptions VALUES ('{error}')")
        connection.commit()
        print(f"error: {error}")

    return answers


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'token' not in state:
        token = handle_token()
        state['token'] = token['token']

    state['error'] = ''
    categories_array = get_categories()
    state["categories"] = categories_array

    cat = 9
    question_array = []

    if request.method == "POST" and request.values.get("colours"):
        cat = request.values.get("colours")
        state['skips'] = int(state['skips'])-1

    if request.method == "POST" and request.values.get('add_skip') and int(state['coins']) > 0:
        state['skips'] = int(state['skips']) + 1
        state['coins'] = int(state['coins']) - 1

    if request.method == "POST" and request.values.get('check'):
        lst = list(request.values.get("check").split(","))
        t = check_answer(lst[1], lst[0], lst[2], 1)
        p = lst[3].strip()
        updated_cat = cursor.execute(
            f'SELECT id FROM categories where name="{p}"').fetchall()
        if not updated_cat:
            updated_cat = 9
        cscores = check_scores()
        scores = get_scores()
        state["scores"] = scores
        state["current_cat"] = p
        # print(f"cat get: {updated_cat[0][0]}")
        diff = manage_difficulty(scores[4], scores[3])
        try:
            question_array = get_question(updated_cat[0][0], state['token'], diff)
            answers = build_answer_array(question_array)
            quest = (''.join(char for char in question_array['question'] if char.isalnum())).lower()
            cans_str = (''.join(char for char in question_array['correct_answer'] if char.isalnum())).lower()
        except Exception as error:
            cursor.execute(f"INSERT INTO exceptions VALUES ('{error}')")
            connection.commit()
            print(f"request: {request.values}")
            print(f"updated_cat: {updated_cat}")
            print(f"qarray: {question_array}")
            print(f"error: {error}")
            raise Exception(error)

        return render_template('test.html', title='Welcome', username='name', quest_string=quest,
                               correct_answer=cans_str,
                               question=question_array['question'].replace('&#039;', "'").replace('&quot;',
                                                                                                  '"').replace(
                                   '&rsquo;', '''''').replace('&ldquo;', '"').replace('&amp;', '&')
                               , quest_cat=question_array['category'], answers=sorted(answers, key=lambda x: x[1]),
                               state=state)
    else:
        cscores = check_scores()
        scores = get_scores()
        diff = manage_difficulty(scores[4], scores[3])
        if cat == 9:
            cat = "General Knowledge"
        updated_cat = cursor.execute(
            f'SELECT id FROM categories where name="{cat}"').fetchall()

        question_array = get_question(updated_cat[0][0], state['token'], diff)
        state["current_cat"] = cat
        state["scores"] = scores
        answers = build_answer_array(question_array)
        # print(f"89 - question_array: {question_array}")
        # print(f"92 - answers: {answers}")
        # print(f"96 - question_array['question']: {question_array['question']}")
        quest = (''.join(char for char in question_array['question'] if char.isalnum())).lower()
        cans_str = (''.join(char for char in question_array['correct_answer'] if char.isalnum())).lower()
        return render_template('test.html', title='Welcome', username='name', quest_string=quest,
                               correct_answer=cans_str,
                               question=question_array['question'].replace('&#039;', "'").replace('&rsquo;',
                                                                                                  '''''').replace(
                                   '&quot;', '"').replace('&ldquo;', '"').replace('&amp;', '&'),
                               quest_cat=question_array['category'], answers=answers, state=state)


def get_categories():
    return cursor.execute(
        "SELECT * FROM categories ORDER BY id asc").fetchall()


def handle_token():
    try:
        token_resp = requests.get("https://opentdb.com/api_token.php?command=request")
        token = token_resp.json()
    except Exception as error:
        cursor.execute(f"INSERT INTO exceptions VALUES ('{error}')")
        connection.commit()
        print(f"error: {error}")

    return token


def manage_difficulty(tcount, percentage):
    if not tcount:
        tcount = 0

    if not percentage:
        percentage = 0

    if tcount > 4:
        if percentage >= 70 and percentage < 75:
            diff = 'medium'
        elif percentage >= 75:
            diff = "hard"
        else:
            diff = "easy"
    else:
        diff = "easy"

    state['diff'] = diff
    return diff


def get_data(cat, token, difficulty):
    # print(f"token: {token}")
    # print(f"cat: {cat}")
    a = 0
    while a == 0:
        if int(cat) == 1:
            url = f"https://opentdb.com/api.php?amount=1&token={token}&difficulty={difficulty}"
        else:
            url = f"https://opentdb.com/api.php?amount=1&category={cat}&token={token}&difficulty={difficulty}"
        # print(f"146 - url: {url}")
        try:
            response = requests.get(
                url
            )
            test = response.json()
            # print(f"response: {test['response_code']}")
            if test['response_code'] == 4:
                t = handle_token()
                token = t['token']
            else:
                a = 1
        except Exception as error:
            cursor.execute(f"INSERT INTO exceptions VALUES ('{error}')")
            connection.commit()
            print(f"error: {error}")

        data = response.json()
    return data


def insert_correct_questions(question, user):
    cursor.execute(f"INSERT INTO correct VALUES ('{question}', {user})")
    connection.commit()


def insert_wrong_questions(question, user):
    cursor.execute(f"INSERT INTO wrong VALUES ('{question}', {user})")
    connection.commit()


def select_from_wrong(question):
    t = cursor.execute(
        f"SELECT count(*) FROM wrong where question = '{question}'"
    ).fetchall()
    return t


def select_from_correct(question):
    t = cursor.execute(
        f"SELECT count(*) FROM correct where question = '{question}'"
    ).fetchall()
    return t


def check_answer(question, ans, cans, user):
    check_w = select_from_wrong(question)[0][0]
    check_r = select_from_correct(question)[0][0]

    if ans.strip() == cans.strip():
        if (int(state['scores'][0])+int(state['scores'][1])) > 4:
            state['run'] = int(state['run']) + 1
            if int(state['run']) == 3:
                state['coins'] = int(state['coins']) + 1
                state['run'] = 0
        if check_r == 0:
            ins = insert_correct_questions(question, user)
        return True
    else:
        state['run'] = 0
        if check_w == 0:
            ins = insert_wrong_questions(question, user)
        return False


def remove_punc(text):
    exclude = set(string.punctuation)
    return ''.join(ch for ch in text if ch not in exclude)


def check_scores():
    sc = get_scores()

    ccount_int = float(sc[1])
    wcount_int = float(sc[0])
    tcount = ccount_int + wcount_int

    percent = (ccount_int / (ccount_int + wcount_int)) * 100 if ccount_int > 0 else 0

    if (wcount_int > 5 and tcount < 12) and (int(state['run']) == 0):
        insert = cursor.execute(f"insert into score values({percent},1,{ccount_int})")
        connection.commit()
        state['error'] = "Wrong answers above 5"
        deletec = cursor.execute("delete from correct where user = 1")
        deletew = cursor.execute("delete from wrong where user = 1")
        connection.commit()
        state['skips'] = 5

    if (tcount > 11) and (int(state['run']) == 0):
        if ((percent < 70 and percent > 0)) or (wcount_int > 0 and ccount_int == 0):
            insert = cursor.execute(f"insert into score values({percent},1,{ccount_int})")
            connection.commit()
            state['error'] = "Score below 70%"
            deletec = cursor.execute("delete from correct where user = 1")
            deletew = cursor.execute("delete from wrong where user = 1")
            connection.commit()
            state['skips'] = 5


def get_scores():
    scores = []

    wrong_count = cursor.execute(
        "SELECT count(*) FROM wrong").fetchall()

    scores.append(wrong_count[0][0])
    correct_count = cursor.execute(
        "SELECT count(*) FROM correct").fetchall()
    scores.append(correct_count[0][0])
    high_score = cursor.execute(
        "SELECT max(count) FROM score where user= 1").fetchone()
    scores.append(high_score[0])

    percent = (correct_count[0][0] / (correct_count[0][0] + wrong_count[0][0])) * 100 if correct_count[0][0] > 0 else 0
    scores.append(round(percent, 2))
    total = correct_count[0][0] + wrong_count[0][0]
    scores.append(total)

    return scores


def get_question(cat, token, difficulty):
    question = []
    # print(f"get_question cat: {cat}")
    fresh_data = get_data(cat, token, difficulty)

    # print(f"258 - fresh_data {fresh_data}")
    # print(f"259 - fresh_data results {fresh_data['results']}")

    for i, text in enumerate(fresh_data["results"]):

        new_question = ''.join(char for char in text["question"] if char.isalnum()).lower()
        user_data = cursor.execute(
            f"SELECT question FROM correct where question = '{new_question}'"
        ).fetchone()

        if user_data:  # correct will be saved user data
            continue
        # print(f"268 - text: {text}")
        return text
