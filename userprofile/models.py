# coding=UTF-8
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.template import loader, Context
from django.core.mail import send_mail
from django.conf import settings
from userprofile.countries import CountryField
import datetime
import pickle
import Image, ImageFilter
import os.path

GENDER_CHOICES = ( ('F', _('Female')), ('M', _('Male')),)
GENDER_IMAGES = { "M": "%simages/male.png" % settings.MEDIA_URL, "F": "%simages/female.png" % settings.MEDIA_URL }

class Profile(models.Model):
    """
    User profile model
    """

    firstname = models.CharField(max_length=255, blank=True)
    surname = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(User, unique=True)
    birthdate = models.DateField(default=datetime.date.today(), blank=True)
    date = models.DateTimeField(default=datetime.datetime.now)
    url = models.URLField(blank=True, core=True)
    about = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    country = CountryField()
    location = models.CharField(max_length=255, blank=True)
    public = models.FileField(upload_to="avatars/%Y/%b/%d")

    # avatar
    avatar = models.ImageField(upload_to="avatars/%Y/%b/%d")
    avatartemp = models.ImageField(upload_to="avatars/%Y/%b/%d")
    avatar16 = models.ImageField(upload_to="avatars/%Y/%b/%d")
    avatar32 = models.ImageField(upload_to="avatars/%Y/%b/%d")
    avatar64 = models.ImageField(upload_to="avatars/%Y/%b/%d")
    avatar96 = models.ImageField(upload_to="avatars/%Y/%b/%d")

    def get_genderimage_url(self):
        return GENDER_IMAGES[self.gender]

    def __unicode__(self):
        return _("%s's profile") % self.user

    def get_genderimage_url(self):
        return GENDER_IMAGES[self.gender]

    def visible(self):
        try:
            return pickle.load(open(self.get_public_filename(), "rb"))
        except:
            return dict()

    def get_absolute_url(self):
        return "%sfor/%s/" % (settings.LOGIN_REDIRECT_URL, self.user)

    def yearsold(self):
        return (datetime.date.today().toordinal() - self.birthdate.toordinal()) / 365

    def delete(self):
        for key in [ '', 'temp', '96', '64', '32', '16' ]:
            if getattr(self, "get_avatar%s_filename" % key)():
                try:
                    os.remove(getattr(self, "get_avatar%s_filename" % key)())
                except:
                    pass
        try:
            os.remove(self.public)
        except:
            pass 
        super(Profile, self).delete()

    def save(self):
        if not self.public:
            public = dict()
            for item in self.__dict__.keys():
                public[item] = False
            public["user_id"] = True
            public["avatar"] = True
            self.save_public_file("%s.public" % self.user, pickle.dumps(public))
        super(Profile, self).save()

class ValidationManager(models.Manager):

    def verify(self, key):
        try:
            verify = self.get(key=key)
            if not verify.is_expired():
                if verify.get_type_display() == "password":
                    return True
                elif verify.get_type_display() == "validation":
                    verify.user.email = verify.email
                    verify.user.save()
                    verify.delete()
                    return True
                else:
                    return False
            else:
                verify.delete()
                return False
        except:
            return False

    def getuser(self, key):
        try:
            return self.get(key=key).user
        except:
            return False

    def add(self, user, type, email):
        """
        Add a new validation process entry
        """
        while True:
            key = User.objects.make_random_password(70)
            try:
                Validation.objects.get(key=key)
            except Validation.DoesNotExist:
                self.key = key
                break

        template_body = "userprofile/email/%s.txt" % type
        template_subject = "userprofile/email/%s_subject.txt" % type
        site_name, domain = Site.objects.get_current().name, Site.objects.get_current().domain
        body = loader.get_template(template_body).render(Context(locals()))
        subject = loader.get_template(template_subject).render(Context(locals())).strip()
        send_mail(subject=subject, message=body, from_email=None, recipient_list=[email])
        user = User.objects.get(username=str(user))
        type_choices = { "validation": 1, "password": 2 }
        self.filter(user=user, type=type_choices[type]).delete()
        return self.create(user=user, key=key, type=type_choices[type], email=email)

class Validation(models.Model):
    type = models.PositiveSmallIntegerField(choices=( (1, 'validation'), (2, 'password'),))
    user = models.ForeignKey(User)
    email = models.EmailField(blank=True)
    key = models.CharField(max_length=70, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    objects = ValidationManager()

    class Meta:
        unique_together = ('type', 'user')

    def __unicode__(self):
        return _("Email validation process for %(user)s of type %(type)s") % { 'user': self.user, 'type': self.get_type_display() }

    def is_expired(self):
        return (datetime.datetime.today() - self.created).days > 0

    def resend(self):
        """
        Resend validation email
        """
        type = self.get_type_display()
        template_body = "userprofile/email/%s.txt" % type
        template_subject = "userprofile/email/%s_subject.txt" % type
        site_name, domain = Site.objects.get_current().name, Site.objects.get_current().domain
        key = self.key
        body = loader.get_template(template_body).render(Context(locals()))
        subject = loader.get_template(template_subject).render(Context(locals())).strip()
        send_mail(subject=subject, message=body, from_email=None, recipient_list=[self.email])
        self.created = datetime.datetime.now()
        self.save()
        return True

