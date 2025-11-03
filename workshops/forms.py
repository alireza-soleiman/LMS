from django import forms
from .models import Stakeholder, Problem, Project , Objective , Indicator

# workshops/forms.py
class StakeholderForm(forms.ModelForm):
    class Meta:
        model = Stakeholder
        fields = ['name', 'interest', 'power']


class ProblemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super(ProblemForm, self).__init__(*args, **kwargs)
        if project:
            # Parent dropdown filters
            self.fields['parent'].queryset = Problem.objects.filter(project=project).exclude(problem_type='EFFECT')
        self.fields['parent'].required = False

    class Meta:
        model = Problem
        # *** Ensure 'color' is included in this list ***
        fields = ['description', 'problem_type', 'parent', 'color']
        labels = {
            'parent': 'Which problem does this relate to?',
            'color': 'Node Color (Optional)', # Add a label for the color field
        }
        # *** Add or Correct this widgets dictionary ***
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }

class ObjectiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super(ObjectiveForm, self).__init__(*args, **kwargs)
        if project:
            # The parent dropdown should only show desired situations or other objectives
            self.fields['parent'].queryset = Objective.objects.filter(project=project).exclude(objective_type='IMPACT')
        self.fields['parent'].required = False

    class Meta:
        model = Objective
        fields = ['description', 'objective_type', 'parent', 'color']
        labels = {
            'parent': 'Which objective does this relate to?',
            'objective_type': 'Objective Type',
            'color': 'Node Color (Optional)',
        }
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }

class IndicatorForm(forms.ModelForm):
    class Meta:
        model = Indicator
        fields = ['name', 'description', 'accepted']
