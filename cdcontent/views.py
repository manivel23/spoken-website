from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.core.servers.basehttp import FileWrapper
from django.core.context_processors import csrf
from django.contrib.auth.models import User
from django.shortcuts import render
from django.conf import settings
from django.db.models import Q
from creation.models import *
from cdcontent.forms import *
import os, tempfile, zipfile
import json

# Create your views here.
def zipdir(src_path, dst_path, archive):
    for root, dirs, dir_files in os.walk(src_path):
        for dir_file in dir_files:
            archive.write(os.path.join(root, dir_file), os.path.join(dst_path, dir_file))

def humansize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.1f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def get_sheet_path(foss, lang, sheet):
    file_path = settings.MEDIA_ROOT + 'videos/' + str(foss.id) + '/' + foss.foss.replace(' ', '-') + '-' + sheet.title() + '-Sheet-' + lang.name + '.pdf'
    if lang.name != 'English':
        if os.path.isfile(file_path):
            new_file_path = 'spoken/videos/' + str(foss.id) + '/' + foss.foss.replace(' ', '-') + '-' + sheet.title() + '-Sheet-' + lang.name + '.pdf'
            return file_path, new_file_path
    
    file_path = settings.MEDIA_ROOT + 'videos/' + str(foss.id) + '/' + foss.foss.replace(' ', '-') + '-' + sheet.title() + '-Sheet-English.pdf'
    if os.path.isfile(file_path):
            new_file_path = 'spoken/videos/' + str(foss.id) + '/' + foss.foss.replace(' ', '-') + '-' + sheet.title() + '-Sheet-English.pdf'
            return file_path, new_file_path
    return False, False


def home(request):
    if request.method == 'POST':
        form = CDContentForm(request.POST)
        if form.is_valid():
            temp = tempfile.TemporaryFile()
            archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
            selectedfoss = json.loads(request.POST.get('selected_foss', {}))
            all_rows = []
            all_foss_details = {}
            for key, values in selectedfoss.iteritems():
                foss_rec = FossCategory.objects.get(pk = key)
                level = int(values[1])
                for value in values[0]:
                    language = Language.objects.get(pk = value)
                    src_path, dst_path = get_sheet_path(foss_rec, language, 'instruction')
                    if dst_path:
                        archive.write(src_path, dst_path)
                    src_path, dst_path = get_sheet_path(foss_rec, language, 'installation')
                    if dst_path:
                        archive.write(src_path, dst_path)
                    if level:
                        tr_recs = TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss_id = key, tutorial_detail__level_id = level, language_id = value).order_by('tutorial_detail__level', 'tutorial_detail__order', 'language__name')
                    else:
                        tr_recs = TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss_id = key, language_id = value).order_by('tutorial_detail__level', 'tutorial_detail__order', 'language__name')
                    rec = None
                    for rec in tr_recs:
                        all_rows.append(rec)
                        filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/' + rec.video
                        if os.path.isfile(settings.MEDIA_ROOT + filepath):
                            archive.write(settings.MEDIA_ROOT + filepath, 'spoken/' + filepath)
                        ptr = filepath.rfind(".")
                        filepath = filepath[:ptr] + '.srt'
                        if os.path.isfile(settings.MEDIA_ROOT + filepath):
                            archive.write(settings.MEDIA_ROOT + filepath, 'spoken/' + filepath)
                        if rec.common_content.slide_status > 0:
                            filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/resources/' + rec.common_content.slide
                            if os.path.isfile(settings.MEDIA_ROOT + filepath):
                                archive.write(settings.MEDIA_ROOT + filepath, 'spoken/' + filepath)
                        if rec.common_content.assignment_status > 0 and rec.common_content.assignment_status != 6:
                            filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/resources/' + rec.common_content.assignment
                            if os.path.isfile(settings.MEDIA_ROOT + filepath):
                                archive.write(settings.MEDIA_ROOT + filepath, 'spoken/' + filepath)
                        if rec.common_content.code_status > 0 and rec.common_content.code_status != 6:
                            filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/resources/' + rec.common_content.code
                            if os.path.isfile(settings.MEDIA_ROOT + filepath):
                                archive.write(settings.MEDIA_ROOT + filepath, 'spoken/' + filepath)
                        tutorial_path = str(rec.tutorial_detail.foss_id) + '/' + str(rec.tutorial_detail_id) + '/'
                        ctx = {
                            'tr_rec': rec,
                            'tr_recs': tr_recs,
                            'media_path': settings.MEDIA_ROOT,
                            'tutorial_path': tutorial_path,
                        }
                        watch_page = str(render(request, "cdcontent/templates/watch_tutorial.html", ctx))
                        watch_page = watch_page.replace('Content-Type: text/html; charset=utf-8', '')
                        watch_page = watch_page.strip("\n")
                        archive.writestr('spoken/videos/' + tutorial_path + 'show-video-' + rec.language.name + '.html', watch_page)
                    if rec != None:
                        try:
                            tmp = all_foss_details[foss_rec.id]
                        except:
                            all_foss_details[foss_rec.id] = {}
                        all_foss_details[foss_rec.id]['foss'] = foss_rec.foss
                        try:
                            tmp = all_foss_details[foss_rec.id]['langs']
                        except:
                            all_foss_details[foss_rec.id]['langs'] = {}
                        all_foss_details[foss_rec.id]['langs'][rec.language_id] = rec.language.name
            archive.write(settings.BASE_DIR + '/static/spoken/css/bootstrap.min.css', 'spoken/includes/css/bootstrap.min.css')
            archive.write(settings.BASE_DIR + '/static/spoken/css/font-awesome.min.css', 'spoken/includes/css/font-awesome.min.css')
            archive.write(settings.BASE_DIR + '/static/spoken/css/main.css', 'spoken/includes/css/main.css')
            archive.write(settings.BASE_DIR + '/static/spoken/css/video-js.min.css', 'spoken/includes/css/video-js.min.css')
            archive.write(settings.BASE_DIR + '/static/spoken/images/favicon.ico', 'spoken/includes/images/favicon.ico')
            archive.write(settings.BASE_DIR + '/static/spoken/images/logo.png', 'spoken/includes/images/logo.png')
            archive.write(settings.BASE_DIR + '/static/spoken/js/jquery-1.11.0.min.js', 'spoken/includes/js/jquery-1.11.0.min.js')
            archive.write(settings.BASE_DIR + '/static/spoken/js/bootstrap.min.js', 'spoken/includes/js/bootstrap.min.js')
            archive.write(settings.BASE_DIR + '/static/spoken/js/video.js', 'spoken/includes/js/video.js')
            archive.write(settings.BASE_DIR + '/static/spoken/images/thumb-even.png', 'spoken/includes/images/thumb-even.png')
            archive.write(settings.BASE_DIR + '/static/spoken/images/Basic.png', 'spoken/includes/images/Basic.png')
            archive.write(settings.BASE_DIR + '/static/spoken/images/Intermediate.png', 'spoken/includes/images/Intermediate.png')
            archive.write(settings.BASE_DIR + '/static/spoken/images/Advanced.png', 'spoken/includes/images/Advanced.png')
            zipdir(settings.BASE_DIR + '/static/spoken/fonts', 'spoken/includes/fonts/', archive)
            list_page = str(render(request, "cdcontent/templates/tutorial_search.html", {'collection': all_rows, 'foss_details': all_foss_details}))
            list_page = list_page.replace('Content-Type: text/html; charset=utf-8', '')
            list_page = list_page.strip("\n")
            archive.writestr('spoken/index.html', list_page)
            archive.writestr('spoken/README.txt', 'Open the "index.html" file in Chrome/Firefox/Safari web browser to access the videos.\n\nNote:\n------\nIf you are using Firefox, then type "about:config" on address bar. Once the config page is loaded, then click on "I\'ll be more careful, I promise!" button. Then search for the option "security.fileuri.strict_origin_policy" and change the value to "false", this step is mandatory to load the web fonts offline.')
            archive.close()
            wrapper = FileWrapper(temp)
            response = HttpResponse(wrapper, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename=spoken-tutorial-cdcontent.zip'
            response['Content-Length'] = temp.tell()
            temp.seek(0)
            return response
    else:
        form = CDContentForm()
    context = {
        'form': form
    }
    context.update(csrf(request))

    return render(request, "cdcontent/templates/cdcontent_home.html", context)

@csrf_exempt
def ajax_fill_languages(request):
    data = ''
    fossid = request.POST.get('foss', '')
    levelid = int(request.POST.get('level', 0))
    if fossid:
        if levelid:
            lang_recs = TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss_id = fossid, tutorial_detail__level_id = levelid).values_list('language_id', 'language__name').order_by('language__name').distinct()
        else:
            lang_recs = TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss_id = fossid).values_list('language_id', 'language__name').order_by('language__name').distinct()
        for row in lang_recs:
            data = data + '<option value="' + str(row[0]) + '">' + row[1] + '</option>'

    return HttpResponse(json.dumps(data), mimetype='application/json')

@csrf_exempt
def ajax_add_foss(request):
    foss = request.POST.get('foss', '')
    level = int(request.POST.get('level', 0))
    selectedfoss = {}
    try:
        langs = json.loads(request.POST.get('langs', []))
    except:
        langs = []
    try:
        selectedfoss = json.loads(request.POST.get('selectedfoss', ''))
    except:
        pass
    if foss and langs:
        selectedfoss[foss] = [langs, level]
    data = json.dumps(selectedfoss)

    return HttpResponse(json.dumps(data), mimetype='application/json')

@csrf_exempt
def ajax_show_added_foss(request):
    try:
        tmp = json.loads(request.POST.get('selectedfoss', {}))
    except:
        tmp = {}
    data = ''
    fsize_total = 0.0
    print '--------------'
    for key, values in tmp.iteritems():
        foss = FossCategory.objects.get(pk = key)
        level = int(values[1])
        print foss, level
        langs = ', '.join(list(Language.objects.filter(id__in = list(values[0])).order_by('name').values_list('name', flat=True)))
        if level:
            tr_recs = TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss = foss, tutorial_detail__level_id = level, language_id__in = list(values[0]))
        else:
            tr_recs = TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss = foss, language_id__in = list(values[0]))
        fsize = 0.0
        for rec in tr_recs:
            try:
                filepath = 'videos/' + str(foss.id) + '/' + str(rec.tutorial_detail_id) + '/' + rec.video
                if os.path.isfile(settings.MEDIA_ROOT + filepath):
                    fsize += os.path.getsize(settings.MEDIA_ROOT + filepath)
                ptr = filepath.rfind(".")
                filepath = filepath[:ptr] + '.srt'
                if os.path.isfile(settings.MEDIA_ROOT + filepath):
                    fsize += os.path.getsize(settings.MEDIA_ROOT + filepath)
                if rec.common_content.slide_status > 0:
                    filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/resources/' + rec.common_content.slide
                    if os.path.isfile(settings.MEDIA_ROOT + filepath):
                        fsize += os.path.getsize(settings.MEDIA_ROOT + filepath)
                if rec.common_content.assignment_status > 0 and rec.common_content.assignment_status != 6:
                    filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/resources/' + rec.common_content.assignment
                    if os.path.isfile(settings.MEDIA_ROOT + filepath):
                        fsize += os.path.getsize(settings.MEDIA_ROOT + filepath)
                if rec.common_content.code_status > 0 and rec.common_content.code_status != 6:
                    filepath = 'videos/' + str(key) + '/' + str(rec.tutorial_detail_id) + '/resources/' + rec.common_content.code
                    if os.path.isfile(settings.MEDIA_ROOT + filepath):
                        fsize += os.path.getsize(settings.MEDIA_ROOT + filepath)
            except Exception, e:
                print e
                continue
        fsize_total += fsize
        data += '<tr><td>' + foss.foss + '</td><td>' + langs + '</td><td>' + humansize(fsize) + '</td></tr>'
    if data:
        data += '<tr><td colspan="2" class="col-right">~ Total Size</td><td>' + humansize(fsize_total) + '</td></tr>'
    return HttpResponse(json.dumps(data), mimetype='application/json')
