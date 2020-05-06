import datetime

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from .models import User, Community, Project, MoneySupport, ThingSupport, ThingNecessity


class MoneySupportTestCase(TestCase):
    def setUp(self):
        admin = User.objects.create(
            first_name="Test", second_name="Tasty", last_name="Testing")
        community = Community.objects.create(
            name='test legal entity',
            bulstat='000',
            text='',
            email='test@email.com',
            phone='000',
            admin=admin,
        )
        project = Project.objects.create(
            type='c',
            name='test project',
            description='',
            text='',
            community=community,
        )
        necessity = ThingNecessity.objects.create(
            project=project,
            name='test thing necessity',
            description='',
            price=100,
            count=3,
        )

        self.money_support = lambda leva: MoneySupport.objects.create(
            leva=leva,
            project=project,
            user=admin,
            necessity=necessity)

    def test_simple(self):
        """When big enough money support is accepted a thing support is created"""
        self.money_support(100).set_accepted()
        self.assertQuerysetEqual(ThingSupport.objects.all(), [
                                 '<ThingSupport: Test (test thing necessity)>'])

    def test_multiple(self):
        """When enough money supports are accepted a thing support is created"""
        self.money_support(50).set_accepted()
        self.money_support(50).set_accepted()

        self.assertQuerysetEqual(ThingSupport.objects.all(), [
                                 '<ThingSupport: Test (test thing necessity)>'])

    def test_huge(self):
        """When a huge money support is accepted multiple thing supports are created up to the amount needed, the reminder goes to an unaccepted money support"""

        money_support = self.money_support(400)
        money_support.set_accepted()

        self.assertQuerysetEqual(ThingSupport.objects.all(
        ), 3*['<ThingSupport: Test (test thing necessity)>'], ordered=False)

        self.assertQuerysetEqual(MoneySupport.objects.filter(comment='reminder from %d' % money_support.id).all(), [
                                 '<MoneySupport: Test (100.0) for test thing necessity>'])

    def test_little(self):
        """When a little money support is accepted no thing support is created"""

        self.money_support(10).set_accepted()

        self.assertQuerysetEqual(ThingSupport.objects.all(), [])
