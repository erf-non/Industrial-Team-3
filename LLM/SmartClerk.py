# -*- coding: utf-8 -*-
import google.generativeai as genai
import os
import pathlib
import textwrap

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown


# def to_markdown(text):
#   text = text.replace('•', '  *')
#   return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


def response(message):
    api_key = ''
    genai.configure(api_key = api_key)

    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    with open('prompt.txt', 'r', encoding = 'utf-8') as good:
      defult = good.read()
    msg = message
    prompt = defult + msg
    chat = model.start_chat(history=[])
    response = chat.send_message(prompt)
    # print(type(response.text))
    return(response.text)

print(response("Fuck you"))