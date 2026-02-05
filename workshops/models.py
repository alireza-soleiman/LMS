from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Project(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🧠 Store Workshop 0 / 1 data (overview, etc.)
    overview = models.JSONField(default=dict, blank=True)

    # 🌳 Workshop 2.3 – Objective Tree (already in use)
    objective_tree = models.JSONField(default=dict, blank=True)

    # 🧩 Workshop 5 – Scenario Building (Q-Methodology)
    # All actions, q-sorts, scenarios will be stored here as JSON
    scenario_data = models.JSONField(default=dict, blank=True)

    # 👥 Team information
    group_name = models.CharField(max_length=255, blank=True, null=True)
    # list of {name, surname, student_number, email}
    members = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.title} ({self.owner.username})"


class Stakeholder(models.Model):
    LEVEL_CHOICES = [
        ('International', 'International'),
        ('National', 'National'),
        ('Regional', 'Regional'),
        ('Provincial', 'Provincial'),
        ('Local', 'Local'),
    ]
    TYPOLOGY_CHOICES = [
        ('Political', 'Political actors'),
        ('Bureaucratic', 'Bureaucratic actors'),
        ('Special', 'Special interests'),
        ('General', 'General interests'),
        ('Experts', 'Experts'),
    ]
    RESOURCES_CHOICES = [
        ('Political', 'Political resources'),
        ('Economic', 'Economic resources'),
        ('Legal', 'Legal resources'),
        ('Cognitive', 'Cognitive resources'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stakeholders')
    name = models.CharField(max_length=150)
    interest = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    power = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='Local')
    typology = models.CharField(max_length=20, choices=TYPOLOGY_CHOICES, default='General')
    resources = models.CharField(max_length=20, choices=RESOURCES_CHOICES, default='Cognitive')

    def __str__(self):
        return self.name


class Problem(models.Model):
    PROBLEM_TYPE_CHOICES = [
        ('CORE', 'Core Problem'),
        ('CAUSE', 'Cause'),
        ('EFFECT', 'Effect'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='problems')
    description = models.CharField(max_length=255)
    problem_type = models.CharField(max_length=10, choices=PROBLEM_TYPE_CHOICES, default='CAUSE')

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Select a color (e.g., #FF0000)"
    )

    def __str__(self):
        return self.description


class Objective(models.Model):
    OBJECTIVE_TYPE_CHOICES = [
        ('SITUATION', 'Desired Situation'),
        ('OBJECTIVE', 'Objective (Means)'),
        ('IMPACT', 'Impact (End)'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='objectives')
    description = models.CharField(max_length=255)
    objective_type = models.CharField(max_length=10, choices=OBJECTIVE_TYPE_CHOICES, default='OBJECTIVE')

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Select a color (e.g., #FF0000)"
    )

    def __str__(self):
        return self.description


class MasterIndicator(models.Model):
    category = models.CharField(max_length=255, blank=True, null=True)
    criterion = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


class Indicator(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='indicators')
    master_indicator = models.ForeignKey(MasterIndicator, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    criterion = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)
    accepted = models.BooleanField(default=False)
    added_by_student = models.BooleanField(default=False)
    order = models.PositiveIntegerField(null=True, blank=True)
    white_cards_after = models.PositiveIntegerField(default=0)
    weight = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


class IndicatorRanking(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='rankings')
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    weight = models.FloatField(default=0.0)
    white_cards_after = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position']


class QSortResult(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="qsort_results")
    participant_id = models.CharField(max_length=64)
    participant_label = models.CharField(max_length=255, blank=True)
    sort_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = self.participant_label or self.participant_id
        return f"QSortResult: {label}"


class SWOTItem(models.Model):
    CATEGORY_CHOICES = [
        ('S', 'Strength'),
        ('W', 'Weakness'),
        ('O', 'Opportunity'),
        ('T', 'Threat'),
    ]
    project = models.ForeignKey(Project, related_name='swot_items', on_delete=models.CASCADE)
    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"
