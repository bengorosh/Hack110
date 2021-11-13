# main.py

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from flask import Flask, session, redirect, url_for, escape, request, Response, abort, Markup
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_wtf import FlaskForm, FlaskForm
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
import json
from datetime import date
import numpy as np
import pandas as pd
import datetime
import math


main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

#@main.route('/profile')
#@login_required
#def profile():
#    return render_template('profile.html', name=current_user.name)

###############

sections_file = "FinanceEducationApp/fin_lit_sections.txt"
survey_file = "FinanceEducationApp/fin_lit_survey.txt"
questionaire_file = "FinanceEducationApp/fin_lit_questions.txt"
num_questions_to_display = 3

#populate once at init by reading section files
#use pandas DataFrame

#list of sections
#columns are: section no, section name
sections = pd.read_csv(sections_file, sep=',')
sections.set_index(['section_no'])
total_sections = sections.section_no.max()

#initial survey questions
#columns are: section no, quotesion no, question text, answer1 text, answer2 text, answer3 text, answer4 text
survey = pd.read_csv(survey_file, sep=',')
survey.set_index(['section_no','question_no'])

#daily questions
#columns are: section no, quotesion no, question text, answer1 text, answer2 text, answer3 text, answer4 text, correct answer, recommendation text
questions = pd.read_csv(questionaire_file, sep=',')
questions.set_index(['section_no','question_no'])

#populate a dictionary of section no to max number of available questions
section_max_questions = {}

for x in questions.section_no.unique():
    section_max_questions[x]=questions[questions.section_no==x].question_no.max()

# returns True if user already completed initial survey
def is_survey_completed(username):
    user_answers = pd.read_csv(get_filename_for_user(username), sep=',', names=['username','section_no','question_no','is_correct_answer','date'], header=None)
    user_answers.set_index(['section_no','question_no'])
    user_answers = user_answers[user_answers.username == username]
    if user_answers[user_answers.question_no == 0].question_no.count() >= 1:
        return True
    else:
        return False

# for a give user, return the map with 3 questions (key:secton_no, value:question) we want user to focus on today
# for now it just returns the next question to show from every section
def select_daily_questions(username):
    with open(get_filename_for_user(username),"a+") as fo:
        fo.close()

    user_answers = pd.read_csv(get_filename_for_user(username), sep=',', names=['username','section_no','question_no','is_correct_answer','date'], header=None)
    user_answers.set_index(['section_no','question_no'])
    user_answers = user_answers[user_answers.username == username]
    user_max_answer_per_section = {}

    #find top 5 section to display
    #by sorting already answered section such as those with least correct answers on top
    section_asnwers = user_answers.groupby('section_no')['is_correct_answer'].sum().reset_index().sort_values(by='is_correct_answer')
    sections=section_asnwers.section_no.values[:num_questions_to_display].tolist()

    #check which sections haven't been answered yet
    missing_section = []
    for i in range(1,total_sections+1):
        if i not in section_asnwers.section_no.values:
            missing_section.append(i)
    print("missing: " + str(missing_section))

    selected_sections=[]

    #show missing section before any section already with answers
    for i in range(1,num_questions_to_display+1):
        if len(missing_section) >= i:
            selected_sections.append(missing_section[i-1])

    #add sections of focus until we have 5 sections
    populated_sections = len(selected_sections)
    if populated_sections < num_questions_to_display:
        for i in range (0, num_questions_to_display-populated_sections):
            selected_sections.append(sections[i])

    user_max_answer_per_section = {}
    for x in selected_sections:
        user_max_answer = user_answers[user_answers.section_no == x].question_no.max()
        #if there are no answers yet, show the first question
        max_answer = 1 if math.isnan(user_max_answer) else user_max_answer + 1
        #if the user answered all questions in a section, continue showing last question
        max_answer = min(max_answer, section_max_questions[x])
        user_max_answer_per_section[x] = max_answer
    return user_max_answer_per_section

#generate a standard user answers file name
def get_filename_for_user(username):
    #use one file for everyone
    return "daily_answers.csv"

@main.route('/profile', methods = ['GET', 'POST'])
@login_required
def profile():
    username = current_user.name
    if request.method == 'POST':
        with open(get_filename_for_user(username),"a+") as fo:
            questions_answered = "" #str(request.form.keys())
            for x in request.form.keys():
                questions_answered += request.form[x]
                sec_ques_array = x.split("_")
                section_no = sec_ques_array[0]
                question_no = sec_ques_array[1]
                fo.writelines(username+","+section_no+","+question_no+","+request.form[x]+","+datetime.datetime.now().strftime("%Y-%m-%d")+"\r\n")
            fo.close()
        return redirect(url_for('main.daily_question'))
    else:
        if is_survey_completed(username):
            return redirect(url_for('main.daily_question'))

        questions_html = ""
        for index, row in survey.iterrows():
            question_no = str(row["section_no"]) + "_" + str(row["question_no"])
            questions_html += "<p class='question_styles'>"+row["question_text"]+"</p><p class='answer_styles'>"
            for y in range(1,5):
                questions_html += '<input align="left" type="radio" name="' + question_no + '" value="' + str(2-y) +'" required>' + row["answer"+str(y)+"_text"] + '</br>'
            questions_html += "</p><br><br>"

        form_prefix_html = """
        <div class="container">
            <p class='title_styles'>Please answer the following initial survey questions</p><br>

            <form action = "" method = "post">
        """

        form_suffix_html = """
                <button type="submit" class="button">Submit Answer</button>
            </form>
        """.format(uname=username)

        return render_template('profile.html', name=current_user.name, form_content=Markup(form_prefix_html + questions_html + form_suffix_html))

@main.route('/daily_question', methods = ['GET', 'POST'])
@login_required
def daily_question():
    username = current_user.name
    if request.method == 'POST':
        with open(get_filename_for_user(username),"a+") as fo:
            questions_answered = "" #str(request.form.keys())
            recommendation_text = ""
            for x in request.form.keys():
                questions_answered += request.form[x]
                sec_ques_array = x.split("_")
                section_no = sec_ques_array[0]
                question_no = sec_ques_array[1]
                question = questions[(questions["section_no"] == int(section_no)) & (questions["question_no"] == int(question_no))]
                is_correct_answer = int(request.form[x]) == question.correct_answer_no.values[0]
                if is_correct_answer == False:
                    recommendation_text += " <br> " + str(question["recommendation_text"].values[0])
                fo.writelines(username+","+section_no+","+question_no+","+str(int(is_correct_answer))+","+datetime.datetime.now().strftime("%Y-%m-%d")+"\r\n")
            fo.close()
        recommendation_text_json = json.dumps(str(recommendation_text))
        session['recommendations'] = recommendation_text_json
        return redirect(url_for('main.thankyou', recommendations = recommendation_text_json))

    else:
        questions_html = ""
        daily_questions = select_daily_questions(current_user.name)
        for x in daily_questions.keys():
            question = questions[(questions["section_no"] == x) & (questions["question_no"] == daily_questions[x])]
            question_no = str(x) + "_" + str(daily_questions[x])
            questions_html += "<p> <span class='question_styles'>"+question.question_text.values[0] + "</span> "
            questions_html += "<br style='height: 10px;'> <span class='section_styles'>" + sections[sections["section_no"] == x].section_name.values[0]+"</span> </p>"
            questions_html += "<p class='answer_styles'>"
            for y in range(1,5):
                questions_html += '<input align="left" type="radio" name="' + question_no + '" value="' + str(y) +'">' + question["answer"+str(y)+"_text"].values[0] + '</br>'
            questions_html += "</p><br><br>"

        form_prefix_html = """
            <div class="container">
                <p class='title_styles'>Please answer the following daily questions and get immediate feedback</p><br>

               <form action = "" method = "post">

        """

        form_suffix_html = """
                <button type="submit" class="button">Submit Answer</button>
            </form>
        """.format(uname=username)

        return render_template('profile.html', name=current_user.name, form_content=Markup(form_prefix_html + questions_html + form_suffix_html))

@main.route('/thankyou')
@login_required
def thankyou():
    recommendations = request.args['recommendations']
    recommendations = session['recommendations']

    html_prefix = """
            <div class="container">
                <h3>Here is some additional information based on your answers</h3>
    """
    html_suffix = """
                <br><br>
                <h3><a href = '/daily_question' class="txtlink2"></b>Answer more questions any time and learn more</b></a></h3>
            </div>
    """
    html_inline = """ <br> <p class='answer_styles'> Congratulations! You answered all questions correctly!</p>"""
    if recommendations != "":
        html_inline = "<p class='answer_styles'> " + json.loads(recommendations)

    return render_template('profile.html', name=current_user.name, form_content=Markup(html_prefix + html_inline + html_suffix))
