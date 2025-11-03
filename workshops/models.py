from django.db import models
from django.contrib.auth.models import User
# Import validators to enforce number range
from django.core.validators import MinValueValidator, MaxValueValidator

class Project(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


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
    # --- NEW: Choices for the Resources field ---
    RESOURCES_CHOICES = [
        ('Political', 'Political resources'),
        ('Economic', 'Economic resources'),
        ('Legal', 'Legal resources'),
        ('Cognitive', 'Cognitive resources'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stakeholders')
    name = models.CharField(max_length=150)
    interest = models.PositiveIntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    power = models.PositiveIntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='Local')
    typology = models.CharField(max_length=20, choices=TYPOLOGY_CHOICES, default='General')

    # --- UPDATED: 'resources' is now a single CharField ---
    resources = models.CharField(max_length=20, choices=RESOURCES_CHOICES, default='Cognitive')

    def __str__(self):
        return self.name


# workshops/models.py

class Problem(models.Model):
    # This new field is the key to our new logic
    PROBLEM_TYPE_CHOICES = [
        ('CORE', 'Core Problem'),
        ('CAUSE', 'Cause'),
        ('EFFECT', 'Effect'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='problems')
    description = models.CharField(max_length=255)

    # We add the problem_type field
    problem_type = models.CharField(max_length=10, choices=PROBLEM_TYPE_CHOICES, default='CAUSE')

    # A problem's parent is the problem it relates to (e.g., a Cause's parent is a Core Problem)
    # We change the related_name to be more generic.
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    # Stores hex color code, e.g., #RRGGBB. Allow blank, use default later.
    color = models.CharField(max_length=7, blank=True, null=True, help_text="Select a color (e.g., #FF0000)")

    def __str__(self):
        return self.description



class Objective(models.Model):
    # Define the types based on the PDF diagram
    OBJECTIVE_TYPE_CHOICES = [
        ('SITUATION', 'Desired Situation'),
        ('OBJECTIVE', 'Objective (Means)'),
        ('IMPACT', 'Impact (End)'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='objectives')
    description = models.CharField(max_length=255)
    objective_type = models.CharField(max_length=10, choices=OBJECTIVE_TYPE_CHOICES, default='OBJECTIVE')

    # Self-referencing link, just like the Problem model
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    # We include the color field from the start
    color = models.CharField(max_length=7, blank=True, null=True, help_text="Select a color (e.g., #FF0000)")

    def __str__(self):
        return self.description

# workshops/models.py  (add this after Objective or at the bottom)

class Indicator(models.Model):
    """
    Indicators used in WS3 (Indicator Selection).
    Each Indicator belongs to a Project (so each project/group sees its own set).
    'accepted' -> selected in Phase 1 (Delphi).
    'added_by_student' -> true if student added a custom indicator.
    'order' -> integer ranking order (1 = top priority). Null if not ranked yet.
    'white_cards_after' -> number of white cards inserted after this indicator (0..4).
    'weight' -> computed normalized weight (float).
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='indicators')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    accepted = models.BooleanField(default=False)
    added_by_student = models.BooleanField(default=False)
    order = models.PositiveIntegerField(null=True, blank=True)
    white_cards_after = models.PositiveSmallIntegerField(default=0, help_text="0=weak ... 4=extreme")
    weight = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accepted', 'order', 'name']

    def __str__(self):
        return f"{self.name} ({'accepted' if self.accepted else 'not accepted'})"
