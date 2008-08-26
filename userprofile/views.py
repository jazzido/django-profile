from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext as _
from userprofile.forms import AvatarForm, AvatarCropForm, EmailValidationForm, \
                              ProfileForm, RegistrationForm, LocationForm, \
                              PublicFieldsForm
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.db import models
from django.contrib.auth.models import User
from userprofile.models import EmailValidation, Avatar
from django.template import RequestContext
from django.core.validators import email_re
from django.conf import settings
from xml.dom import minidom
import urllib2
import random
import cPickle as pickle
import base64
import Image
import urllib
import os

if not settings.AUTH_PROFILE_MODULE:
    raise SiteProfileNotAvailable
try:
    app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
    Profile = models.get_model(app_label, model_name)
except (ImportError, ImproperlyConfigured):
    raise SiteProfileNotAvailable

if hasattr(settings, "DEFAULT_AVATAR") and settings.DEFAULT_AVATAR:
    DEFAULT_AVATAR = settings.DEFAULT_AVATAR
else:
    DEFAULT_AVATAR = os.path.join(settings.MEDIA_ROOT, "generic.jpg")

if not os.path.isfile(DEFAULT_AVATAR):
    import shutil
    image = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         "generic.jpg")
    shutil.copy(image, DEFAULT_AVATAR)

GOOGLE_MAPS_API_KEY = hasattr(settings, "GOOGLE_MAPS_API_KEY") and \
                      settings.GOOGLE_MAPS_API_KEY or None
AVATAR_WEBSEARCH = hasattr(settings, "AVATAR_WEBSEARCH") and \
                   settings.AVATAR_WEBSEARCH or None

if AVATAR_WEBSEARCH:
    import gdata.service
    import gdata.photos.service

def get_profiles():
    return Profile.objects.order_by("-date")

def fetch_geodata(request, lat, lng):
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        url = "http://ws.geonames.org/countrySubdivision?lat=%s&lng=%s" % (lat, lng)
        dom = minidom.parse(urllib.urlopen(url))
        country = dom.getElementsByTagName('countryCode')
        if len(country) >=1:
            country = country[0].childNodes[0].data
        region = dom.getElementsByTagName('adminName1')
        if len(region) >=1:
            region = region[0].childNodes[0].data

        return HttpResponse(simplejson.dumps({'success': True, 'country': country, 'region': region}))
    else:
        raise Http404()

def public(request, username):
    try:
        profile = User.objects.get(username=username).get_profile()
    except:
        raise Http404

    template = "userprofile/profile/public.html"
    data = { 'profile': profile, 'GOOGLE_MAPS_API_KEY': GOOGLE_MAPS_API_KEY, }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def searchimages(request):
    """
    Web search for images Form
    """

    images = dict()
    if request.method=="POST" and request.POST.get('keyword'):
        keyword = request.POST.get('keyword')
        gd_client = gdata.photos.service.PhotosService()
        feed = gd_client.SearchCommunityPhotos("%s&thumbsize=72c" % keyword.split(" ")[0], limit='48')
        for entry in feed.entry:
            images[entry.media.thumbnail[0].url] = entry.content.src

    template = "userprofile/avatar/search.html"
    data = { 'section': 'avatar', 'images': images, }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def overview(request):
    """
    Main profile page
    """
    profile, created = Profile.objects.get_or_create(user=request.user)
    validated = False
    try:
        email = EmailValidation.objects.get(user=request.user).email
    except EmailValidation.DoesNotExist:
        email = request.user.email
        if email: validated = True

    template = "userprofile/profile/overview.html"
    data = { 'section': 'overview', 'GOOGLE_MAPS_API_KEY': GOOGLE_MAPS_API_KEY,
             'email': email, 'validated': validated }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def personal(request):
    """
    Personal data of the user profile
    """
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("profile_edit_personal_done"))
    else:
        form = ProfileForm(instance=profile)

    template = "userprofile/profile/personal.html"
    data = { 'section': 'personal', 'GOOGLE_MAPS_API_KEY': GOOGLE_MAPS_API_KEY,
             'form': form, }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def location(request):
    """
    Location selection of the user profile
    """
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = LocationForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("profile_edit_location_done"))
    else:
        form = LocationForm(instance=profile)

    template = "userprofile/profile/location.html"
    data = { 'section': 'location', 'GOOGLE_MAPS_API_KEY': GOOGLE_MAPS_API_KEY,
             'form': form, }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def delete(request):
    if request.method == "POST":
        # Remove the profile and all the information
        Profile.objects.filter(user=request.user).delete()
        EmailValidation.objects.filter(user=request.user).delete()
        Avatar.objects.filter(user=request.user).delete()

        # Remove the e-mail of the account too
        request.user.email = ''
        request.user.first_name = ''
        request.user.last_name = ''
        request.user.save()

        return HttpResponseRedirect(reverse("profile_delete_done"))

    template = "userprofile/profile/delete.html"
    data = { 'section': 'delete', }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def avatarchoose(request):
    """
    Avatar choose
    """
    profile, created = Profile.objects.get_or_create(user = request.user)
    if not request.method == "POST":
        form = AvatarForm()
    else:
        form = AvatarForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data.get('url') or form.cleaned_data.get('photo')
            avatar = Avatar(user=request.user, image=image, valid=False)
            avatar.image.save("%s.jpg" % request.user.username, image)
            image = Image.open(avatar.image.path)
            image.thumbnail((480, 480), Image.ANTIALIAS)
            image.convert("RGB").save(avatar.image.path, "JPEG")
            avatar.save()
            return HttpResponseRedirect('%scrop/' % request.path_info)

            base, filename = os.path.split(avatar_path)
            generic, extension = os.path.splitext(filename)

    if DEFAULT_AVATAR:
        base, filename = os.path.split(DEFAULT_AVATAR)
        filename, extension = os.path.splitext(filename)
        generic96 = "%s/%s.96%s" % (base, filename, extension)
        generic96 = generic96.replace(settings.MEDIA_ROOT, settings.MEDIA_URL)
    else:
        generic96 = ""

    template = "userprofile/avatar/choose.html"
    data = { 'generic96': generic96, 'form': form,
             'AVATAR_WEBSEARCH': AVATAR_WEBSEARCH, 'section': 'avatar', }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def avatarcrop(request):
    """
    Avatar management
    """
    avatar = get_object_or_404(Avatar, user=request.user, valid=False)
    if not request.method == "POST":
        form = AvatarCropForm()
    else:
        form = AvatarCropForm(request.POST)
        if form.is_valid():
            top = int(form.cleaned_data.get('top'))
            left = int(form.cleaned_data.get('left'))
            right = int(form.cleaned_data.get('right'))
            bottom = int(form.cleaned_data.get('bottom'))

            image = Image.open(avatar.image.path)
            box = [ left, top, right, bottom ]
            image = image.crop(box)
            if image.mode not in ('L', 'RGB'):
                image = image.convert('RGB')

            image.save(avatar.image.path)
            avatar.valid = True
            avatar.save()
            return HttpResponseRedirect(reverse("profile_avatar_crop_done"))

    template = "userprofile/avatar/crop.html"
    data = { 'section': 'avatar', 'avatar': avatar, 'form': form, }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def avatardelete(request, avatar_id=False):
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        try:
            Avatar.objects.get(user=request.user, valid=True).delete()
            return HttpResponse(simplejson.dumps({'success': True}))
        except:
            return HttpResponse(simplejson.dumps({'success': False}))
    else:
        raise Http404()

def email_validation_process(request, key):
    """
    Verify key and change email
    """
    if EmailValidation.objects.verify(key=key):
        successful = True
    else:
        successful = False

    template = "userprofile/account/email_validation_done.html"
    data = { 'successful': successful, }
    return render_to_response(template, data, context_instance=RequestContext(request))

def email_validation(request):
    """
    E-mail Change form
    """
    if request.method == 'POST':
        form = EmailValidationForm(request.POST)
        if form.is_valid():
            EmailValidation.objects.add(user=request.user, email=form.cleaned_data.get('email'))
            return HttpResponseRedirect('%sprocessed/' % request.path_info)
    else:
        form = EmailValidationForm()

    template = "userprofile/account/email_validation.html"
    data = { 'form': form, }
    return render_to_response(template, data, context_instance=RequestContext(request))

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            newuser = User.objects.create_user(username=username, email='', password=password)

            if form.cleaned_data.get('email'):
                newuser.email = form.cleaned_data.get('email')
                EmailValidation.objects.add(user=newuser, email=newuser.email)

            newuser.save()
            return HttpResponseRedirect('%scomplete/' % request.path_info)
    else:
        form = RegistrationForm()

    template = "userprofile/account/registration.html"
    data = { 'form': form, }
    return render_to_response(template, data, context_instance=RequestContext(request))

@login_required
def email_validation_reset(request):
    """
    Resend the validation email for the authenticated user.
    """
    try:
        resend = EmailValidation.objects.get(user=request.user).resend()
        response = "done"
    except EmailValidation.DoesNotExist:
        response = "failed"

    return HttpResponseRedirect(reverse("email_validation_reset_response", 
            args=[response]))
