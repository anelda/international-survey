#!/usr/bin/env python
# -*- coding: utf-8 -*-


__author__ = 'Olivier Philippe'


"""
Limesurvey offers the possibility to import/export a TSV file containing all the information
of the survey structure. Using this possibility, this script aims to translate the files used
by the different groups to creates their survey, into a compatible TSV file.
It take only the argument of the folder where all the information is stored, and create a new
compatible file.
All information about the TSV file structure can be retrieved here:
    https://manual.limesurvey.org/Tab_Separated_Value_survey_structure
"""

import csv
import sys
import os
from collections import OrderedDict
from include.logger import logger
from config.config import creationConfig as main_config
import importlib
from markdown import markdown

RUNNING = 'dev'

if RUNNING == 'dev':
    DEBUGGING='DEBUG'
elif RUNNING == 'prod':
    DEBUGGING='INFO'

logger = logger(name='creating survey', stream_level=DEBUGGING)


def import_config(folder):
    """
    Import the config file associated with the folder name
    """
    module = 'config.{}'.format(folder)
    return importlib.import_module(module).config()


def create_empty_row():
    """
    Create an Ordered dictionary to be used to translate csv file to tsv
    """
    return OrderedDict((k, '') for k in main_config.main_headers)


def init_outfile(folder):
    """
    Rewrite over the existing file to avoid issue of appending and
    return the path to the file
    """
    outfile_name = folder + '_to_import.txt'
    outfile = os.path.join(folder, outfile_name)
    with open(outfile, 'w') as f:
        w = csv.DictWriter(f, delimiter='\t',
                           lineterminator='\n',
                           quotechar='"',
                           fieldnames=main_config.main_headers)
        w.writeheader()
    return outfile


def read_survey_file(folder):
    """
    Read the survey csv file and yield each line as a dictionary
    """
    question_file = os.path.join(folder, '.'.join([folder, 'csv']))
    with open(question_file, 'r') as f:
        csv_f = csv.DictReader(f)
        for row in csv_f:
            yield row


def write_row_outfile(outfile, row):
    """
    """
    with open(outfile, 'a') as f:
        w = csv.DictWriter(f, delimiter='\t',
                           lineterminator='\n',
                           quotechar='"',
                           fieldnames=main_config.main_headers)
        w.writerow(row)


def to_modify(original_list, modified_list):
    """
    """
    return_list = list()
    for element in original_list:
        replaced = False
        for e in modified_list:
            if element['name'] == e['name']:
                return_list.append(e)
                replaced = True
                break
        if replaced is False:
            return_list.append(element)
    return return_list


def to_add(original_list, list_to_add):
    """
    """
    for obj in list_to_add:
        original_list.insert(obj[1], obj[0])
    return original_list


def create_header(main_config, specific_config):
    """
    """
    good_parameters = to_modify(main_config.global_headers, specific_config.header_to_modify)
    good_parameters = to_add(main_config.global_headers, specific_config.header_to_add)
    return good_parameters


def add_from_list(outfile, list_to_copy):
    """
    """
    for element in list_to_copy:
        row = create_empty_row()
        row.update(element)
        write_row_outfile(outfile, row)


def get_text(folder, type_message, lang=None):
    """
    """
    if lang:
        filename = '{}_message_{}.md'.format(type_message, lang)
    else:
        filename = '{}_message.md'.format(type_message)

    folder = os.path.join(folder, 'texts')
    path = os.path.join(folder, filename)
    with open(path, 'r') as f:
            return markdown(f.read())


def add_text_message(full_list, message, type_message):
    """
    """
    return_list = list()
    message_done = False
    for element in full_list:
        if message_done is False:
            if element['name'] == 'surveyls_welcometext' and type_message == 'welcome':
                message_done = True
                element['text'] = message
            elif element['name'] == 'surveyls_endtext' and type_message == 'welcome':
                message_done = True
                element['text'] = message
        return_list.append(element)
    return return_list


def create_description(main_config, specific_config, welcome_message, end_message):
    """
    """
    good_description = to_modify(main_config.global_description, specific_config.description_to_modify)
    good_description = to_add(main_config.global_description, specific_config.description_to_add)
    good_description = add_text_message(good_description, welcome_message, 'welcome')
    good_description = add_text_message(good_description, end_message, 'end')
    return good_description


def get_answer(folder, file_answer):
    """
    """
    outfile = os.path.join(folder, 'listAnswers', '{}.csv'.format(file_answer))
    with open(outfile, 'r') as f:
        return [x[:-1] for x in f.readlines()]


def main():
    # Get which survey
    folder = sys.argv[1]

    # Import specific config file
    specific_config = import_config(folder)

    # Init an empty survey file
    outfile = init_outfile(folder)

    # Create a copy the header to the empty file
    config_header = create_header(main_config, specific_config)

    # Record the copy into the file
    add_from_list(outfile, config_header)

    # Get the welcome message
    welcome_message = get_text(folder, 'welcome')

    # Get the end message
    end_message = get_text(folder, 'end')

    # Create the description
    config_description = create_description(main_config, specific_config,
                                            welcome_message, end_message)

    # Copy the description to the header
    for el in config_description:
        print(el)
    # print(config_description)
    add_from_list(outfile, config_description)

    # Open the survey file
    nbr_section = 0
    section = main_config.group_format
    # type/scale are like 'G0', 'G1', etc.
    section['type/scale'] = 'G' + str(nbr_section)  # need to recorded as a string in the output file
    section['language'] = 'en'
    write_row_outfile(outfile, section)
    for row in read_survey_file(folder):
        if int(row['section']) - 1 != nbr_section:
            # -1 because the section numbers starts at 0 but
            # in the csv survey_file it starts at 1
            nbr_section = int(row['section']) - 1
            section = main_config.group_format
            # type/scale are like 'G0', 'G1', etc.
            section['type/scale'] = 'G' + str(nbr_section)
            section['language'] = 'en'
            write_row_outfile(outfile, section)

        if row['answer_format'].lower() == 'one choice':
            # Create the question
            question = main_config.one_choice_question
            question['name'] = row['code']
            question['text'] = row['question']
            question['language'] = 'en'
            question['other'] = 'Y'
            write_row_outfile(outfile, question)
            # Add the answers
            # Create an inc to add to the question code. They need unique label
            n = 1
            for text_answer in get_answer(folder, row['answer_file']):
                answer_row = main_config.one_choice_answer
                # answer_row['name'] = 'A' + str(n)
                answer_row['name'] = str(n)
                answer_row['text'] = text_answer.split(';')[0].strip('"')
                answer_row['language'] = 'en'
                write_row_outfile(outfile, answer_row)
                n +=1

        if row['answer_format'].lower() == 'ranking':
            # Ranking questions work differently
            # First a list of rank SQ class need to be created (max 8 here)
            # Then only the questions are created
            # As neither of them have specific value for database, they are
            # created here and not pulled from the config file
            question = main_config.ranking_question
            question['name'] = row['code']
            question['text'] = row['question']
            question['language'] = 'en'
            write_row_outfile(outfile, question)
            # Create the Subquestion ranks
            for i in range(1, 9):  # To get 8 ranked questions
                init_row = {'class': 'SQ', 'type/scale': '0', 'name': str(i), 'relevance': '1',
                       'text': 'Rank ' + str(i), 'language': 'en'}
                write_row_outfile(outfile, init_row)


            n = 1
            for text_answer in get_answer(folder, row['answer_file']):
                answer_row = main_config.ranking_answer
                answer_row['name'] = str(n)
                answer_row['text'] = text_answer.split(';')[0].strip('"')
                answer_row['language'] = 'en'
                write_row_outfile(outfile, answer_row)
                n +=1

        if row['answer_format'].lower() == 'likert':
            pass

        if row['answer_format'].lower() == 'freenumeric':
            pass

        if row['answer_format'].lower() == 'freetext':
            pass

        if row['answer_format'].lower() == 'multiple choice':
            pass
    # Check for condition

    # Do everything for the new language


if __name__ == "__main__":
    main()
