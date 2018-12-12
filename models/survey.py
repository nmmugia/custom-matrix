# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError


def dict_keys_startswith(dictionary, string):
    """Returns a dictionary containing the elements of <dict> whose keys start with <string>.
        .. note::
            This function uses dictionary comprehensions (Python >= 2.7)
    """
    return {k: v for k, v in dictionary.items() if k.startswith(string)}

def dict_keys_endswith(dictionary, string):
    return {k: v for k, v in dictionary.items() if k.endswith(string)}

def dict_keys_endswith_line(dictionary, string1, string2):
    """ Return dict for user input line, which search the value from the string (ends with string AND not start with string)"""
    return {k: v for k, v in dictionary.items() if k.endswith(string1) and not k.startswith(string2)}

def dict_remove_unneeded_keys(dictionary):
    """ remove [0] which is a dummy"""
    return {k: v for k, v in dictionary.items() if not k.endswith('[0]')}

def dict_remove_unneeded_vals(dictionary):
    return {k: v for k, v in dictionary.items() if not v == ''}

class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    matrix_subtype = fields.Selection([('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row'), ('custom_row', 'Custom Matrix'), ('editable_row', 'Editable Row')], string='Matrix Type', default='simple')

class SurveyLabel(models.Model):
    _inherit = 'survey.label'
    type = fields.Selection([
            ('free_text', 'Multiple Lines Text Box'),
            ('textbox', 'Single Line Text Box'),
            ('numerical_box', 'Numerical Value'),
            ('dropdown', 'Dropdown'),
            ('checkbox', 'Checkbox')
            ], string='Type of Question', default="checkbox")

    dpvalues = fields.Many2many('dp.attributes.value', string="values")
    user_input_id = fields.Many2one('survey.user_input', string="Column")
    user_input_id_2 = fields.Many2one('survey.user_input', string="Row")

class SurveyLabelManyTags(models.Model):
    _name = 'dp.attributes.value'

    name = fields.Char("Name")

class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input_line'

    answer_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('free_text', 'Free Text'),
        ('suggestion', 'Suggestion'), ('dropdown', 'Dropdown')], string='Answer Type')

    value_dropdown = fields.Many2one('dp.attributes.value', string="Value Dropdown")
    matrix_subtype_id = fields.Selection(related='question_id.matrix_subtype', string="Matrix subtype")

    @api.model
    def save_line_matrix(self, user_input_id, question, post, answer_tag, survey_id):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': survey_id,
            'skipped': False
        }
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', survey_id),
            ('question_id', '=', question.id)
        ])
        old_uil.sudo().unlink()

        no_answers = True
        ca_dict = dict_keys_startswith(post, answer_tag + '_')

        comment_answer = ca_dict.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer})
            self.create(vals)
            no_answers = False

        if question.matrix_subtype == 'simple':
            for row in question.labels_ids_2:
                a_tag = "%s_%s" % (answer_tag, row.id)
                if a_tag in ca_dict:
                    no_answers = False
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca_dict[a_tag], 'value_suggested_row': row.id})
                    self.create(vals)

        elif question.matrix_subtype == 'multiple':
            for col in question.labels_ids:
                for row in question.labels_ids_2:
                    a_tag = "%s_%s_%s" % (answer_tag, row.id, col.id)
                    if a_tag in ca_dict:
                        no_answers = False
                        vals.update({'answer_type': 'suggestion', 'value_suggested': col.id, 'value_suggested_row': row.id})
                        self.create(vals)
        elif question.matrix_subtype == 'custom_row':
            for col in question.labels_ids:
                for row in question.labels_ids_2:
                    a_tag = "%s_%s_%s" % (answer_tag, row.id, col.id)
                    if a_tag in ca_dict:
                        no_answers = False
                        if post.get(a_tag): 
                            sline = a_tag.split('_')[-1]
                            label_obj = question.labels_ids.browse(int(sline))
                            if label_obj.type == 'textbox':
                                vals.update({'answer_type': 'text', 'value_suggested': col.id, 'value_suggested_row': row.id, 'value_text': post.get(a_tag)})
                            elif label_obj.type == 'free_text':
                                vals.update({'answer_type': 'free_text', 'value_suggested': col.id, 'value_suggested_row': row.id, 'value_free_text': post.get(a_tag)})
                            elif label_obj.type == 'numerical_box':
                                vals.update({'answer_type': 'number', 'value_suggested': col.id, 'value_suggested_row': row.id, 'value_number': post.get(a_tag)})
                            elif label_obj.type == 'date':
                                vals.update({'answer_type': 'date', 'value_suggested': col.id, 'value_suggested_row': row.id, 'value_date': post.get(a_tag)})
                            elif label_obj.type == 'dropdown':
                                vals.update({'answer_type': 'dropdown', 'value_suggested': col.id, 'value_suggested_row': row.id, 'value_dropdown': int(post.get(a_tag))})
                            else:
                                vals.update({'answer_type': 'suggestion', 'value_suggested': col.id, 'value_suggested_row': row.id})
                            self.create(vals)
        elif question.matrix_subtype == 'editable_row':
            label_dict = dict_keys_startswith(post, 'label[')
            answer_lines = dict_keys_endswith_line(post, ']', 'label[')
            label_dict = dict_remove_unneeded_keys(label_dict)
            answer_lines = dict_remove_unneeded_keys(answer_lines)
            answer_lines = dict_remove_unneeded_vals(answer_lines)
            label_dict = dict_remove_unneeded_vals(label_dict)
            i = 1
            for key, val in label_dict.items():
                label_vals = {
                    'value': val,
                    'type': 'checkbox',
                    'question_id_2': question.id,
                    'user_input_id_2': user_input_id
                }
                # if key != 'label[0]':
                #     label = self.env['survey.label'].create(label_vals)
                label = self.env['survey.label'].create(label_vals)
                col_vals = {k: v for k, v  in  answer_lines.items() if k.endswith('['+str(i)+']')}
                col_test = ()
                for col_key,col_val in sorted(col_vals.items()):
                    # to fix
                    no_answers = False
                    col_obj = ""
                    if col_val: 
                        # col_obj = re.sub("["+str(i)+"]","",col_key)
                        for c in col_key:
                            if c == '[':
                                break
                            col_obj += c
                        col_obj = col_obj.split('[')[0].split('_')[-1]
                        label_obj = self.env['survey.label'].search([('id', '=', col_obj)])
                        if label_obj.type == 'textbox':
                            vals.update({'answer_type': 'text', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_text': col_val})
                        elif label_obj.type == 'free_text':
                            vals.update({'answer_type': 'free_text', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_free_text': col_val})
                        elif label_obj.type == 'numerical_box':
                            vals.update({'answer_type': 'number', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_number': float(col_val)})
                        elif label_obj.type == 'date':
                            vals.update({'answer_type': 'date', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_date': col_val})
                        elif label_obj.type == 'dropdown':
                            vals.update({'answer_type': 'dropdown', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_dropdown': int(col_val)})
                        else:
                            vals.update({'answer_type': 'suggestion', 'value_suggested': col_obj, 'value_suggested_row': label.id})
                        self.create(vals)
                i += 1
            row_post = {}
            test = ()
            row_label = self.env['survey.label'].search([('question_id_2', '=', question.id), ('user_input_id_2', '=', user_input_id)])
            for rl in row_label.ids:
                for k, v in post.items():
                    try:
                        if rl == int(k.split('[')[0].split('_')[-1]):
                            rl = self.env['survey.label'].search([('id', '=', rl)])
                            rl.write({'value': v})
                        if rl == int(k.split('_')[-2]):
                            col_obj = self.env['survey.label'].search([('id', '=', int(k.split('_')[-1]))])
                            if col_obj.type == 'textbox':
                                vals.update({'answer_type': 'text', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_text': col_val})
                            elif col_obj.type == 'free_text':
                                vals.update({'answer_type': 'free_text', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_free_text': col_val})
                            elif col_obj.type == 'numerical_box':
                                vals.update({'answer_type': 'number', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_number': float(col_val)})
                            elif col_obj.type == 'date':
                                vals.update({'answer_type': 'date', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_date': col_val})
                            elif col_obj.type == 'dropdown':
                                vals.update({'answer_type': 'dropdown', 'value_suggested': col_obj, 'value_suggested_row': label.id, 'value_dropdown': int(col_val)})
                            else:
                                vals.update({'answer_type': 'suggestion', 'value_suggested': col_obj, 'value_suggested_row': label.id})
                            self.create(vals)
                    except ValueError:
                        continue
            raise UserError((test))
        if no_answers:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(vals)
        return True