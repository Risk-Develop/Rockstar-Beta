from django import forms

class PayrollFinalizeForm(forms.Form):
    month = forms.IntegerField(min_value=1, max_value=12)
    year = forms.IntegerField(min_value=2000, max_value=2100)
    cutoff = forms.ChoiceField(choices=[('1','1st'),('2','2nd')])
