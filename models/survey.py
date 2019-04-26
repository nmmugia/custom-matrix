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
        ('suggestion', 'Suggestion'),
        ('dropdown', 'Dropdown'),
        ('attachment', 'Attachment')], string='Answer Type')

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

        no_answers = True
        #16_783_18_297_297
        # ca_dict = dict_keys_startswith(post, answer_tag + '_')

        # comment_answer = ca_dict.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        # if comment_answer:
        #     vals.update({'answer_type': 'text', 'value_text': comment_answer})
        #     self.create(vals)
        #     no_answers = False

        if question.matrix_subtype == 'simple':
            old_uil.sudo().unlink()
            for row in question.labels_ids_2:
                # a_tag = "%s_%s" % (answer_tag, row.id)
                # if a_tag in ca_dict:
                # raise UserError(([post, ca_dict]))
                vals.update({'answer_type': 'suggestion', 'value_suggested': post[answer_tag], 'value_suggested_row': row.id})
                self.create(vals)
            no_answers = False

        if question.matrix_subtype == 'multiple':
            if post['checked'] == 'true':
                if old_uil:
                    old_val = tuple(ol.value_suggested.id for ol in  old_uil)
                    if int(post[answer_tag]) not in old_val:
                        vals.update({'answer_type': 'suggestion', 'answer_type': 'suggestion', 'value_suggested': int(post[answer_tag])})
                        self.create(vals)
                else:
                    vals.update({'answer_type': 'suggestion', 'value_suggested': int(post[answer_tag])})
                    self.create(vals)
            else:
                old_uil = self.search([
                    ('user_input_id', '=', user_input_id),
                    ('survey_id', '=', survey_id),
                    ('question_id', '=', question.id),
                    ('value_suggested', '=', int(post[answer_tag]))
                ])
                old_uil.sudo().unlink()
            no_answers = False
        elif question.matrix_subtype == 'custom_row':
            # answer_tag ,row, col
            sline = answer_tag.split('_')
            label_obj = question.labels_ids.browse(int(sline[-1]))
            old_uil = self.search([
                ('user_input_id', '=', user_input_id),
                ('survey_id', '=', survey_id),
                ('question_id', '=', question.id),
                ('value_suggested', '=', int(sline[-1])),
                ('value_suggested_row', '=', int(sline[-2]))
            ])
            old_uil.sudo().unlink()
            if label_obj.type == 'textbox':
                vals.update({'answer_type': 'text', 'value_suggested': int(sline[-1]), 'value_suggested_row': int(sline[-2]), 'value_text': post.get(answer_tag)})
            elif label_obj.type == 'free_text':
                vals.update({'answer_type': 'free_text', 'value_suggested': int(sline[-1]), 'value_suggested_row': int(sline[-2]), 'value_free_text': post.get(answer_tag)})
            elif label_obj.type == 'numerical_box':
                vals.update({'answer_type': 'number', 'value_suggested': int(sline[-1]), 'value_suggested_row': int(sline[-2]), 'value_number': post.get(answer_tag)})
            elif label_obj.type == 'date':
                vals.update({'answer_type': 'date', 'value_suggested': int(sline[-1]), 'value_suggested_row': int(sline[-2]), 'value_date': post.get(answer_tag)})
            elif label_obj.type == 'dropdown':
                vals.update({'answer_type': 'dropdown', 'value_suggested': int(sline[-1]), 'value_suggested_row': int(sline[-2]), 'value_dropdown': int(post.get(answer_tag))})
            else:
                vals.update({'answer_type': 'suggestion', 'value_suggested': int(sline[-1]), 'value_suggested_row': int(sline[-2])})
            try:
                if post['checked'] == 'false':
                    old_uil.sudo().unlink()
                else:
                    self.create(vals)
            except KeyError:
                self.create(vals)
            no_answers = False
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
                            rl = rl.id
                        if rl == int(k.split('_')[-2]):
                            col_obj = self.env['survey.label'].search([('id', '=', int(k.split('_')[-1]))])
                            label = self.env['survey.label'].search([('id', '=', int(k.split('_')[-2]))])
                            if col_obj.type == 'textbox':
                                vals.update({'answer_type': 'text', 'value_suggested': col_obj.id, 'value_suggested_row': label.id, 'value_text': v})
                            elif col_obj.type == 'free_text':
                                vals.update({'answer_type': 'free_text', 'value_suggested': col_obj.id, 'value_suggested_row': label.id, 'value_free_text': v})
                            elif col_obj.type == 'numerical_box':
                                vals.update({'answer_type': 'number', 'value_suggested': col_obj.id, 'value_suggested_row': label.id, 'value_number': float(v)})
                            elif col_obj.type == 'date':
                                vals.update({'answer_type': 'date', 'value_suggested': col_obj.id, 'value_suggested_row': label.id, 'value_date': v})
                            elif col_obj.type == 'dropdown':
                                vals.update({'answer_type': 'dropdown', 'value_suggested': col_obj.id, 'value_suggested_row': label.id, 'value_dropdown': int(v)})
                            else:
                                vals.update({'answer_type': 'suggestion', 'value_suggested': col_obj.id, 'value_suggested_row': label.id})
                            self.create(vals)
                    except ValueError:
                        continue
            for rl in row_label.ids:
                label_list = self.search([('question_id', '=', question.id)])
                l_list = ()
                for ll in label_list:
                    l_list += (ll.value_suggested_row.id,)
                l_list = set(l_list)
                if rl not in l_list:
                    self.env['survey.label'].search([('id', '=', rl)]).sudo().unlink()
        return True