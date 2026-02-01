from django.core.management.base import BaseCommand
from clinic.models import Disease


class Command(BaseCommand):
    help = 'Populate initial diseases in the database'

    def handle(self, *args, **options):
        diseases = [
            {'name': 'HIV/AIDS', 'description': 'Human Immunodeficiency Virus infection and acquired immune deficiency syndrome'},
            {'name': 'Tuberculosis', 'description': 'Infectious disease caused by Mycobacterium tuberculosis'},
            {'name': 'Malaria', 'description': 'Mosquito-borne infectious disease'},
            {'name': 'Hepatitis B', 'description': 'Viral infection that attacks the liver'},
            {'name': 'Hepatitis C', 'description': 'Viral infection that causes liver inflammation'},
            {'name': 'Diabetes', 'description': 'Metabolic disorder characterized by high blood sugar'},
            {'name': 'Hypertension', 'description': 'High blood pressure'},
            {'name': 'Cancer', 'description': 'Disease caused by abnormal cell growth'},
            {'name': 'Cardiovascular Disease', 'description': 'Diseases of the heart and blood vessels'},
            {'name': 'Mental Health Disorders', 'description': 'Mental health conditions and disorders'},
        ]

        created_count = 0
        for disease_data in diseases:
            disease, created = Disease.objects.get_or_create(
                name=disease_data['name'],
                defaults={
                    'description': disease_data['description'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created disease: {disease.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {created_count} diseases')
        )