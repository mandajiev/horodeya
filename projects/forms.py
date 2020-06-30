from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import get_language
from projects.models import Answer, MoneySupport
from django.utils.text import slugify
from projects.templatetags.projects_tags import leva
from projects.models import Project, Community, Question, BugReport, EpayMoneySupport
from django.core.exceptions import ValidationError


def question_key(question):
    return 'question_%d' % question.pk


class QuestionForm(forms.Form):
    def __init__(self, *args, **kwargs):
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
                self.fields['necessities'] = forms.CharField(
                    label=label, required=False)
            else:
                if question.prototype.type == 'TextField':
                    field_class = forms.CharField
                else:
                    field_class = getattr(forms, question.prototype.type)

                field = field_class(
                    label=label, help_text=question.description, required=question.required)
                field.initial = self.answer_values.get(key)

                if question.prototype.type == 'ChoiceField':
                    field.widget = forms.RadioSelect()
                    field.choices = [(1, _('Yes')), (2, _('No'))]

                if question.prototype.type == 'TextField':
                    field.widget = forms.Textarea()

                self.fields[key] = field
            self.questions[key] = question

    def save(self, project):
        for question in self.fields.keys():
            if 'question' in question:
                value = self.cleaned_data[question]

                if value is None:
                    value = ''
                answer, created = Answer.objects.update_or_create(
                    project=project,
                    question=self.questions[question],
                    defaults={'answer': value})


class PaymentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        payment_method = kwargs.pop('payment_method')
        payment_amount = kwargs.pop('payment_amount')
        community = kwargs.pop('community')
        super(PaymentForm, self).__init__(*args, **kwargs)

        self.unsupported = False

        self.template = 'projects/payment/' + slugify(payment_method) + '.html'
        self.payment_data = community
        pledge_action_text = _('Pledge to donate') + ' ' + leva(payment_amount)

        if payment_method == MoneySupport.PAYMENT_METHODS.BankTransfer:
            if not community.bank_account_iban:
                self.unsupported = True

            self.fields['accept'] = forms.BooleanField(label=_('I will send the money to the provided bank account within the next 3 days'),
                                                       disabled=self.unsupported, help_text=_("Otherwise the support will be marked invalid"))
            self.action_text = pledge_action_text
        elif payment_method == MoneySupport.PAYMENT_METHODS.Revolut:
            if not community.revolut_phone:
                self.unsupported = True

            self.fields['accept'] = forms.BooleanField(label=_('I will send the money to the provided Revolut account within the next 3 days'),
                                                       disabled=self.unsupported, help_text=_("Otherwise the support will be marked invalid"))
            self.action_text = pledge_action_text

        if self.unsupported:
            self.template = 'projects/payment/unsupported.html'


class ProjectUpdateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['slack_channel']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)


class BugReportForm(forms.ModelForm):

    class Meta:
        model = BugReport
        fields = ['email', 'message']


class EpayMoneySupportForm(forms.ModelForm):

    class Meta:
        model = EpayMoneySupport
        fields = ['amount']
