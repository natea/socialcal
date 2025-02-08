import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from profiles.models import Label
from profiles.forms import LabelForm
from events.models import Event
from django.utils import timezone

User = get_user_model()

@pytest.mark.django_db
class TestLabelFeatures:
    def create_test_user(self, email='test@example.com', password='testpass123'):
        username = email.split('@')[0]
        return User.objects.create_user(username=username, email=email, password=password)

    def test_create_label(self):
        user = self.create_test_user()
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        assert label.name == 'Work'
        assert label.color == '#FF0000'
        assert label.user == user

    def test_label_str_method(self):
        user = self.create_test_user()
        label = Label.objects.create(
            name='Personal',
            color='#0000FF',
            user=user
        )
        assert str(label) == 'Personal (test@example.com)'

    def test_unique_label_name_per_user(self):
        user = self.create_test_user()
        Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        
        form = LabelForm({
            'name': 'Work',
            'color': '#0000FF'
        }, user=user)
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_add_label_view(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        response = client.post(reverse('profiles:add_label'), {
            'name': 'Work',
            'color': '#FF0000'
        })
        assert response.status_code == 302  # Redirect after success
        assert Label.objects.filter(user=user, name='Work').exists()

    def test_add_label_view_ajax(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        response = client.post(
            reverse('profiles:add_label'),
            {
                'name': 'Work',
                'color': '#FF0000'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert response.json()['message'] == 'Label added successfully'
        label = Label.objects.get(user=user, name='Work')
        assert label.color == '#FF0000'

    def test_add_label_view_ajax_validation_error(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        # Create a label first
        Label.objects.create(name='Work', color='#FF0000', user=user)
        
        # Try to create another label with the same name
        response = client.post(
            reverse('profiles:add_label'),
            {
                'name': 'Work',
                'color': '#0000FF'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 400
        assert response.json()['success'] is False
        assert 'name' in response.json()['errors']

    def test_edit_label_view(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        
        response = client.post(
            reverse('profiles:edit_label', kwargs={'label_id': label.id}),
            {'name': 'Work Updated', 'color': '#0000FF'}
        )
        assert response.status_code == 302  # Redirect after success
        label.refresh_from_db()
        assert label.name == 'Work Updated'
        assert label.color == '#0000FF'

    def test_edit_label_view_ajax(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        
        response = client.post(
            reverse('profiles:edit_label', kwargs={'label_id': label.id}),
            {
                'name': 'Work Updated',
                'color': '#0000FF'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert response.json()['message'] == 'Label updated successfully'
        label.refresh_from_db()
        assert label.name == 'Work Updated'
        assert label.color == '#0000FF'

    def test_edit_label_view_ajax_validation_error(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        # Create two labels
        label1 = Label.objects.create(name='Work', color='#FF0000', user=user)
        Label.objects.create(name='Personal', color='#0000FF', user=user)
        
        # Try to update label1 with the name of label2
        response = client.post(
            reverse('profiles:edit_label', kwargs={'label_id': label1.id}),
            {
                'name': 'Personal',
                'color': '#FF0000'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 400
        assert response.json()['success'] is False
        assert 'name' in response.json()['errors']

    def test_delete_label_view(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        
        response = client.post(
            reverse('profiles:delete_label', kwargs={'label_id': label.id})
        )
        assert response.status_code == 302  # Redirect after success
        assert not Label.objects.filter(id=label.id).exists()

    def test_delete_label_view_ajax(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        
        response = client.post(
            reverse('profiles:delete_label', kwargs={'label_id': label.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert response.json()['message'] == 'Label deleted successfully'
        assert not Label.objects.filter(id=label.id).exists()

    def test_label_security(self, client):
        user1 = self.create_test_user('user1@example.com', 'pass123')
        user2 = self.create_test_user('user2@example.com', 'pass123')
        client.force_login(user2)
        
        # Create a label for user1
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user1
        )
        
        # Try to edit user1's label as user2
        response = client.post(
            reverse('profiles:edit_label', kwargs={'label_id': label.id}),
            {'name': 'Hacked', 'color': '#000000'}
        )
        assert response.status_code == 404  # Should not find the label
        
        # Try to delete user1's label as user2
        response = client.post(
            reverse('profiles:delete_label', kwargs={'label_id': label.id})
        )
        assert response.status_code == 404  # Should not find the label
        assert Label.objects.filter(id=label.id).exists()  # Label should still exist

    def test_label_security_ajax(self, client):
        user1 = self.create_test_user('user1@example.com', 'pass123')
        user2 = self.create_test_user('user2@example.com', 'pass123')
        client.force_login(user2)
        
        # Create a label for user1
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user1
        )
        
        # Try to edit user1's label as user2 via AJAX
        response = client.post(
            reverse('profiles:edit_label', kwargs={'label_id': label.id}),
            {'name': 'Hacked', 'color': '#000000'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 404
        
        # Try to delete user1's label as user2 via AJAX
        response = client.post(
            reverse('profiles:delete_label', kwargs={'label_id': label.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 404
        assert Label.objects.filter(id=label.id).exists()  # Label should still exist

    def test_color_validation(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        # Test with invalid color
        response = client.post(
            reverse('profiles:add_label'),
            {
                'name': 'Work',
                'color': 'not-a-color'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 400
        assert response.json()['success'] is False
        assert 'color' in response.json()['errors']

    def test_label_name_required(self, client):
        user = self.create_test_user()
        client.force_login(user)
        
        # Test with empty name
        response = client.post(
            reverse('profiles:add_label'),
            {
                'name': '',
                'color': '#FF0000'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 400
        assert response.json()['success'] is False
        assert 'name' in response.json()['errors']

    def test_delete_label_with_events(self, client):
        """Test deleting a label that is associated with events."""
        user = self.create_test_user()
        client.force_login(user)
        
        # Create label and event
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            user=user
        )
        
        # Associate label with event
        event.labels.add(label)
        
        # Verify association
        assert label in event.labels.all()
        
        # Delete the label
        response = client.post(
            reverse('profiles:delete_label', kwargs={'label_id': label.id})
        )
        
        # Verify redirect
        assert response.status_code == 302
        
        # Verify label is deleted
        assert not Label.objects.filter(id=label.id).exists()
        
        # Verify event still exists and label is removed
        event.refresh_from_db()
        assert Event.objects.filter(id=event.id).exists()
        assert label not in event.labels.all()

    def test_delete_label_with_events_ajax(self, client):
        """Test deleting a label that is associated with events via AJAX."""
        user = self.create_test_user()
        client.force_login(user)
        
        # Create label and event
        label = Label.objects.create(
            name='Work',
            color='#FF0000',
            user=user
        )
        event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            user=user
        )
        
        # Associate label with event
        event.labels.add(label)
        
        # Delete the label via AJAX
        response = client.post(
            reverse('profiles:delete_label', kwargs={'label_id': label.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert response.json()['message'] == 'Label deleted successfully'
        
        # Verify label is deleted
        assert not Label.objects.filter(id=label.id).exists()
        
        # Verify event still exists and label is removed
        event.refresh_from_db()
        assert Event.objects.filter(id=event.id).exists()
        assert label not in event.labels.all() 