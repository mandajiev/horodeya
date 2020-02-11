from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from projects.models import Answer

def question_key(question):
    return 'question_%d' % question.pk

class QuestionForm(forms.Form):
    def __init__ (self, *args, **kwargs):
        questions = kwargs.pop('questions')
        if 'answers' in kwargs:
            answers = kwargs.pop('answers')
        else:
            answers = []
        super(QuestionForm, self).__init__(*args, **kwargs)

        self.answer_values = {}
        for answer in answers:
            self.answer_values[question_key(answer.question)] = answer.answer

        self.questions = {}

        for question in questions:
            label = getattr(question.prototype, 'text_%s' % get_language()) 
            key = question_key(question)
            if question.prototype.type == 'Necessities':
                self.fields['necessities'] = forms.CharField(label=label, required=False)
            else:
                field = getattr(forms, question.prototype.type)(label=label, help_text=question.description, required=question.required)
                field.initial = self.answer_values.get(key)

                if question.prototype.type == 'ChoiceField':
                    field.widget = forms.RadioSelect()
                    field.choices=[(1, _('Yes')), (2, _('No'))]
                self.fields[key] = field
            self.questions[key] = question

    def save(self, time_support):
        for question in self.fields.keys():
            if 'question' in question:
                value = self.cleaned_data[question]
                if value is None:
                    value = ''
                answer, created = Answer.objects.update_or_create(
                    time_support=time_support,
                    question=self.questions[question],
                    defaults={'answer': value})
