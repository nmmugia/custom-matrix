# -*- coding: utf-8 -*-
import json
from odoo import http, _
from odoo.http import request
import logging
from odoo.addons.survey.controllers.main import WebsiteSurvey
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class websitesurvey(WebsiteSurvey):
    @http.route(['/survey/prefill/<model("survey.survey"):survey>/<string:token>',
                 '/survey/prefill/<model("survey.survey"):survey>/<string:token>/<model("survey.page"):page>'],
                type='http', auth='public', website=True)
    def prefill(self, survey, token, page=None, **post):
        UserInputLine = request.env['survey.user_input_line']
        Label = request.env['survey.label']
        ret = {}
        # Fetch previous answers
        if page:
            previous_answers = UserInputLine.sudo().search([('user_input_id.token', '=', token), ('page_id', '=', page.id)])
            previous_label = Label.sudo().search([('user_input_id_2.token', '=', token)])
        else:
            previous_answers = UserInputLine.sudo().search([('user_input_id.token', '=', token)])
            previous_label = Label.sudo().search([('user_input_id_2.token', '=', token)])
        # Return non empty answers in a JSON compatible format
        for label in previous_label:
            answer_tag_label = '%s_%s_%s_%s_%s' % (label.user_input_id_2.survey_id.id, label.question_id_2.page_id.id, label.question_id_2.id, label.user_input_id_2.token, label.id)
            ret.setdefault(answer_tag_label, []).append(label.value)
        for answer in previous_answers:
            if not answer.skipped:
                answer_tag = '%s_%s_%s' % (answer.survey_id.id, answer.page_id.id, answer.question_id.id)
                answer_value = None
                if answer.question_id.matrix_subtype == 'custom_row':
                    if answer.answer_type == 'free_text':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_free_text
                    elif answer.answer_type == 'text':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_text
                    elif answer.answer_type == 'number':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = str(answer.value_number)
                    elif answer.answer_type == 'date':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_date
                    elif answer.answer_type == 'dropdown':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_dropdown.id
                    elif answer.answer_type == 'suggestion' and not answer.value_suggested_row:
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_suggested.id
                    elif answer.answer_type == 'suggestion' and answer.value_suggested_row:
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_suggested.id
                    if answer_value:
                        ret.setdefault(answer_tag, []).append(answer_value)
                    else:
                        _logger.warning("[survey] No answer has been found for question %s marked as non skipped" % answer_tag)
                elif answer.question_id.matrix_subtype == 'editable_row':
                    if answer.answer_type == 'free_text':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_free_text
                    elif answer.answer_type == 'text':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_text
                    elif answer.answer_type == 'number':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = str(answer.value_number)
                    elif answer.answer_type == 'date':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_date
                    elif answer.answer_type == 'dropdown':
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_dropdown.id
                    elif answer.answer_type == 'suggestion' and not answer.value_suggested_row:
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_suggested.id
                    elif answer.answer_type == 'suggestion' and answer.value_suggested_row:
                        answer_tag = "%s_%s_%s" % (answer_tag, answer.value_suggested_row.id, answer.value_suggested.id)
                        answer_value = answer.value_suggested.id
                    if answer_value:
                        ret.setdefault(answer_tag, []).append(answer_value)
                    else:
                        _logger.warning("[survey] No answer has been found for question %s marked as non skipped" % answer_tag)
                else:
                    if answer.answer_type == 'free_text':
                        answer_value = answer.value_free_text
                    elif answer.answer_type == 'text' and answer.question_id.type == 'textbox':
                        answer_value = answer.value_text
                    elif answer.answer_type == 'text' and answer.question_id.type != 'textbox':
                        # here come comment answers for matrices, simple choice and multiple choice
                        answer_tag = "%s_%s" % (answer_tag, 'comment')
                        answer_value = answer.value_text
                    elif answer.answer_type == 'number':
                        answer_value = str(answer.value_number)
                    elif answer.answer_type == 'date':
                        answer_value = answer.value_date
                    elif answer.answer_type == 'suggestion' and not answer.value_suggested_row:
                        answer_value = answer.value_suggested.id
                    elif answer.answer_type == 'suggestion' and answer.value_suggested_row:
                        answer_tag = "%s_%s" % (answer_tag, answer.value_suggested_row.id)
                        answer_value = answer.value_suggested.id
                    if answer_value:
                        ret.setdefault(answer_tag, []).append(answer_value)
                    else:
                        _logger.warning("[survey] No answer has been found for question %s marked as non skipped" % answer_tag)
        return json.dumps(ret)