"""
Management command to load images from a folder structure into an ImageSet.

Expected folder structure:
data_folder/
    real/
        image1.jpg
        image2.png
        ...
    synth/
        image1.jpg
        image2.png
        ...

Usage:
    python manage.py load_imageset <folder_path> <imageset_name> [--description "Description"]
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from evaluator.models import ImageSet, Image, Clinician
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Load images from a folder structure (real/ and synth/) into an ImageSet'

    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path',
            type=str,
            help='Path to the folder containing real/ and synth/ subdirectories'
        )
        parser.add_argument(
            'imageset_name',
            type=str,
            help='Name for the new ImageSet'
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Optional description for the ImageSet'
        )
        parser.add_argument(
            '--admin-username',
            type=str,
            default=None,
            help='Username of the admin creating this ImageSet (optional)'
        )

    def handle(self, *args, **options):
        folder_path = Path(options['folder_path'])
        imageset_name = options['imageset_name']
        description = options['description']
        admin_username = options.get('admin_username')

        # Validate folder structure
        if not folder_path.exists():
            raise CommandError(f"Folder '{folder_path}' does not exist")

        real_folder = folder_path / 'real'
        synth_folder = folder_path / 'synth'

        if not real_folder.exists():
            raise CommandError(f"'real' subfolder not found in '{folder_path}'")
        
        if not synth_folder.exists():
            raise CommandError(f"'synth' subfolder not found in '{folder_path}'")

        # Get admin user if specified
        created_by = None
        if admin_username:
            try:
                created_by = Clinician.objects.get(username=admin_username, is_superuser=True)
            except Clinician.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Admin user '{admin_username}' not found. ImageSet will be created without creator.")
                )

        # Check if ImageSet already exists
        if ImageSet.objects.filter(name=imageset_name).exists():
            raise CommandError(f"ImageSet with name '{imageset_name}' already exists")

        # Create ImageSet
        self.stdout.write(f"Creating ImageSet '{imageset_name}'...")
        image_set = ImageSet.objects.create(
            name=imageset_name,
            description=description,
            created_by=created_by
        )

        # Load real images
        real_count = self._load_images_from_folder(real_folder, image_set, is_real=True)
        
        # Load synthetic images
        synth_count = self._load_images_from_folder(synth_folder, image_set, is_real=False)

        total_count = real_count + synth_count
        
        if total_count == 0:
            image_set.delete()
            raise CommandError("No valid images found in the specified folders")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created ImageSet '{imageset_name}' with {total_count} images "
                f"({real_count} real, {synth_count} synthetic)"
            )
        )

    def _load_images_from_folder(self, folder_path, image_set, is_real):
        """Load all images from a folder into the ImageSet"""
        count = 0
        valid_extensions = {'.jpg', '.jpeg', '.png'}
        
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                try:
                    with open(file_path, 'rb') as f:
                        django_file = File(f, name=file_path.name)
                        
                        Image.objects.create(
                            image_set=image_set,
                            file=django_file,
                            original_filename=file_path.name,
                            is_real=is_real
                        )
                        count += 1
                        self.stdout.write(f"  Loaded: {file_path.name}")
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  Failed to load {file_path.name}: {str(e)}")
                    )
        
        return count
