from django.template.defaultfilters import slugify
from django.contrib import admin
from cms.models import *
from django.conf import settings
from PIL import Image
import glob, os
from cms.forms import *

class SubNavInline(admin.TabularInline):
    model = SubNav
    extra = 0

class NavAdmin(admin.ModelAdmin):
    list_display = ('nav_title', 'permalink', 'position', 'target_new', 'visible', 'created')
    inlines = [SubNavInline]

class BlockAdmin(admin.ModelAdmin):
    form = AdminBodyForm
    list_display = ('title', 'block_location', 'position', 'visible', 'created')

class PageAdmin(admin.ModelAdmin):
    form = CmsPageForm
    list_display = ('title', 'permalink', 'target_new', 'visible', 'created')

class EventAdmin(admin.ModelAdmin):
    form = AdminBodyForm
    exclude = ('user',)
    list_display = ('user', 'title', 'body', 'event_date', 'source_link', 'created')
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()

class NewsTypeAdmin(admin.ModelAdmin):
    exclude = ('slug',)
    list_display = ('name',)
    def save_model(self, request, obj, form, change):
        obj.slug = slugify(request.POST['name'])
        obj.save()

class NewsAdmin(admin.ModelAdmin):
    #form = AdminBodyForm
    form = NewsAdditionaFieldAdmin
    exclude = ('created_by', 'slug')
    list_display = ('title', 'weight', 'picture', 'body', 'url', 'url_title', 'created_by', 'created')
    list_filter = ('news_type',)
    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.picture = None
        obj.slug = slugify(request.POST['title'])
        obj.save()
        
        if 'picture' in request.FILES and request.FILES['picture']:
            obj.picture = request.FILES['picture']
        obj.save()
        
        size = 128, 128
        filename = str(obj.picture)
        file, ext = os.path.splitext(filename)
        if ext != '.pdf' and ext != '':
            im = Image.open(obj.picture)
            im.thumbnail(size, Image.ANTIALIAS)
            ext = ext[1:]
            mimeType = ext.upper()
            if mimeType == 'JPG':
                mimeType = 'JPEG'
            im.save(settings.MEDIA_ROOT + "news/" + str(obj.id) + "/" + str(obj.id) + "-thumb." + ext, mimeType)
        
admin.site.register(Block, BlockAdmin)
admin.site.register(Nav, NavAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(NewsType, NewsTypeAdmin)
admin.site.register(News, NewsAdmin)
