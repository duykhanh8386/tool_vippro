"""Native Studio editor round trip against localhost only, never real accounts."""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from src.module.base import studio_video_from_payload
from src.publishing_browser import PublishingBrowserError, StudioThumbnailBrowser
from src.publishing_thumbnails import ThumbnailReadback
from tests.test_studio_publishing_integration import PAGE, CHANNEL, VIDEO, LocalStudioDriver

STAMP = 4071034800  # 2099-01-02 18:00 UTC+7
REFERENCE = {"title":"เพลงใหม่ 🎵 | Música", "description":"Dòng đầu 🎶\n\n00:00 Canção de Fé\n#Música\n"}
FIELDS = '''<div id="title-textarea"><div id="textbox" contenteditable="true" role="textbox"></div></div>
<div id="description-textarea"><div id="textbox" contenteditable="true" role="textbox"></div></div>'''
EDITOR = '''
<ytcp-video-metadata-visibility><div id="container"><div id="visibility-text"></div></div>
<ytcp-icon-button id="select-button" role="button" style="display:block">Visibility</ytcp-icon-button></ytcp-video-metadata-visibility>
<ytcp-video-visibility-edit-popup><div class="visibility-panel" style="display:none;position:fixed;inset:0;background:white;z-index:1001">
<ytcp-video-visibility-select first-container-style="selected" second-container-style="">
 <div id="first-container"><button name="PUBLIC">Public now</button></div>
 <div id="second-container"><ytcp-icon-button id="second-container-expand-button" role="button" style="display:block">Schedule</ytcp-icon-button>
 <ytcp-visibility-scheduler hidden><ytcp-datetime-picker>
  <ytcp-text-dropdown-trigger id="datepicker-trigger"><ytcp-dropdown-trigger role="button" style="display:block">Date</ytcp-dropdown-trigger></ytcp-text-dropdown-trigger>
  <div id="time-of-day-container"><input type="text"></div>
  <div class="timezone-trigger"><ytcp-button id="timezone-select-button" aria-disabled="false"><button>Timezone</button></ytcp-button>
   <yt-icon aria-label="Local time (GMT+0700)"></yt-icon></div>
 </ytcp-datetime-picker></ytcp-visibility-scheduler></div>
</ytcp-video-visibility-select>
<ytcp-button id="save-button" aria-disabled="true"><button disabled>Done</button></ytcp-button>
</div></ytcp-video-visibility-edit-popup>
<ytcp-date-picker><div class="date-panel" style="display:none;position:fixed;inset:20%;background:white;z-index:1002"><input type="text"></div></ytcp-date-picker>
<ytcp-text-menu><div class="timezone-panel" style="display:none;position:fixed;inset:20%;background:white;z-index:1002">
<tp-yt-paper-item test-id="0" style="display:block">(GMT+0700) Local time</tp-yt-paper-item></div></ytcp-text-menu>
<script>
const config=__CONFIG__,actions=[];
const title=document.querySelector('#title-textarea #textbox'),description=document.querySelector('#description-textarea #textbox');
title.innerText=config.video.title;description.innerText=config.video.description;
const visibilityPanel=document.querySelector('.visibility-panel'),select=document.querySelector('ytcp-video-visibility-select'),
 scheduler=document.querySelector('ytcp-visibility-scheduler'),timeField=document.querySelector('#time-of-day-container input'),
 datePanel=document.querySelector('.date-panel'),dateField=datePanel.querySelector('input'),
 timezonePanel=document.querySelector('.timezone-panel'),popupDone=document.querySelector('#save-button button'),
 badge=document.querySelector('ytcp-video-metadata-visibility #container');
let draftScheduled=config.scheduled,baselineModel,working=false;
scheduler.model=config.model;
function popupEnabled(value){popupDone.disabled=!value;popupDone.parentElement.setAttribute('aria-disabled',value?'false':'true');}
function render(){select.setAttribute('second-container-style',working?'selected':'');select.setAttribute('first-container-style',working?'':'selected');scheduler.hidden=!working;document.querySelector('#second-container-expand-button').hidden=working;timeField.value=String(Math.floor(scheduler.model.selectedTimeOfDayValue/3600)).padStart(2,'0')+':'+String(Math.floor(scheduler.model.selectedTimeOfDayValue%3600/60)).padStart(2,'0');}
badge.className=config.scheduled?'schedule-icon':'private-icon';
file.addEventListener('change',()=>actions.push('thumbnail'));
for(const [node,name] of [[title,'title'],[description,'description']])node.addEventListener('input',()=>{actions.push(name);setSaveEnabled(true);});
for(const host of document.querySelectorAll('ytcp-checkbox-lit')){const handler=host.onclick;host.onclick=event=>{handler(event);actions.push('playlist');};}
document.querySelector('.done-button button').addEventListener('click',()=>actions.push('playlist_done'));
document.querySelector('ytcp-video-metadata-visibility #select-button').onclick=()=>{baselineModel=JSON.parse(JSON.stringify(scheduler.model));working=draftScheduled;render();popupEnabled(false);visibilityPanel.style.display='block';};
document.querySelector('[name=PUBLIC]').onclick=()=>actions.push('PUBLIC_NOW');
document.querySelector('#second-container-expand-button').onclick=()=>{working=true;render();popupEnabled(true);actions.push('schedule');};
document.querySelector('#datepicker-trigger ytcp-dropdown-trigger').onclick=()=>{
 const d=scheduler.model.date,german=document.documentElement.lang.startsWith('de');dateField.value=new Intl.DateTimeFormat(document.documentElement.lang,{year:'numeric',month:german?'2-digit':'short',day:german?'2-digit':'numeric',timeZone:'UTC'}).format(new Date(Date.UTC(d.year,d.month,d.day,12)));
 datePanel.style.display='block';dateField.focus();
};
dateField.onkeydown=event=>{if(event.key!=='Enter')return;event.preventDefault();const value=dateField.value;let parts;
 if(document.documentElement.lang.startsWith('en')){const d=new Date(value);parts={year:d.getFullYear(),month:d.getMonth(),day:d.getDate()};}
 else {const numbers=value.match(/\\d+/g).map(Number);parts={day:numbers[0],month:numbers[1]-1,year:numbers[2]};}
 scheduler.model.date=parts;datePanel.style.display='none';popupEnabled(true);actions.push('date');
};
timeField.onchange=()=>{const match=timeField.value.match(/(\\d+):(\\d+)(?:\\s*([AP]M))?/i);let hour=Number(match[1]);if(match[3])hour=hour%12+(match[3].toUpperCase()==='PM'?12:0);scheduler.model.selectedTimeOfDayValue=hour*3600+Number(match[2])*60;popupEnabled(true);actions.push('time');};
document.querySelector('#timezone-select-button button').onclick=()=>timezonePanel.style.display='block';
document.querySelector('tp-yt-paper-item[test-id="0"]').onclick=()=>{scheduler.model.selectedTimezoneIndex=0;timezonePanel.style.display='none';popupEnabled(true);actions.push('timezone');};
popupDone.onclick=()=>{draftScheduled=working;visibilityPanel.style.display='none';badge.className=draftScheduled?'schedule-icon':'private-icon';setSaveEnabled(true);actions.push('schedule_done');};
document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(datePanel.style.display!=='none')datePanel.style.display='none';else{scheduler.model=JSON.parse(JSON.stringify(baselineModel));visibilityPanel.style.display='none';}}});
save.onclick=async()=>{
 actions.push('save');const model=scheduler.model,d=model.date;
 const stamp=Math.floor((Date.UTC(d.year,d.month,d.day)+model.selectedTimeOfDayValue*1000-420*60000)/1000);
 const descriptionValue=description.innerHTML.toLowerCase()==='<br>'?'':(description.childNodes.length===1 && description.firstChild.nodeType===Node.TEXT_NODE?description.textContent:description.innerText);
 const body={encryptedVideoId:config.video.videoId,nativeEditorCommit:true,actions,title:{newTitle:title.innerText},description:{newDescription:descriptionValue},
  playlists:Array.from(document.querySelectorAll('ytcp-checkbox-lit')).filter(e=>e.querySelector('[role=checkbox]').getAttribute('aria-checked')==='true').map(e=>e.getAttribute('test-id')),
  scheduledPublishing:{set:{timeSec:String(stamp),privacy:'PUBLIC'}},model:JSON.parse(JSON.stringify(model)),draftScheduled};
 if(thumbnailDirty)body.thumbnail={customThumbnail:{externalImageId:'IM-new'}};
 setSaveEnabled(false);
 await fetch('/youtubei/v1/video_manager/metadata_update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
};
</script>'''


class EditorFixture(BaseHTTPRequestHandler):
    def do_GET(self):
        with self.server.lock:
            config=copy.deepcopy(self.server.config)
        page=PAGE.replace('<ytcp-video-metadata-editor><ytcp-thumbnail-editor>', '<ytcp-video-metadata-editor>'+FIELDS+'<ytcp-thumbnail-editor>')
        page=('<!doctype html><html lang="'+config['locale']+'">'+page.replace('<!doctype html>','')+EDITOR+'</html>')
        page=page.replace('__PLAYLISTS__',json.dumps(config['playlists'])).replace('__CONFIG__',json.dumps(config).replace('<','\\u003c'))
        data=page.encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

    def do_POST(self):
        payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with self.server.lock:
            self.server.saves.append(payload)
            if self.server.reject:
                response={'error':{'code':403}}
            else:
                if not payload.get('nativeEditorCommit') or payload.get('draftScheduled') is not True:
                    raise AssertionError('Only the native final editor Save is supported')
                config=self.server.config;video=config['video']
                video.update(title=payload['title']['newTitle'],description=payload['description']['newDescription'])
                if 'thumbnail' in payload:video['thumbnailEditorState']={'customThumbnail':{'externalImageId':'IM-new'},'defaultStill':False,'stillId':0}
                video['scheduledPublishingDetails']={'publishTimeSeconds':payload['scheduledPublishing']['set']['timeSec']}
                # Deliberately retain the stale draft enum that broke API-only
                # confirmation, while the persisted Studio UI is Scheduled.
                video['draftStatus']='DRAFT_STATUS_PUBLIC'
                config.update(model=payload['model'],scheduled=True,playlists=payload['playlists'])
                response={'video':video}
        data=json.dumps(response).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

    def log_message(self,*args):
        pass


@unittest.skipUnless(os.environ.get('TV_PUBLISHING_BROWSER_TESTS')=='1','opt-in localhost Chrome test')
class SingleSaveEditorTests(unittest.TestCase):
    def test_native_single_save_resume_locales_and_rejection(self):
        root=Path(__file__).resolve().parents[1]/'build';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='single-save-editor-',dir=root) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(root.resolve()))
            server=ThreadingHTTPServer(('127.0.0.1',0),EditorFixture)
            server.lock=threading.RLock();server.saves=[];server.reject=False
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            options=webdriver.ChromeOptions();options.add_argument('--headless=new');options.add_argument('--user-data-dir='+str(Path(folder)/'profile'))
            options.set_capability('goog:loggingPrefs',{'performance':'ALL'})
            driver=webdriver.Chrome(service=Service(os.environ['CHROMEDRIVER']),options=options)
            adapter=LocalStudioDriver(driver,f'http://127.0.0.1:{server.server_port}')
            image=Path(folder)/'song.jpg';image.write_bytes(b'fixture')
            channel=SimpleNamespace(id=CHANNEL,cookies=[])
            baseline={'videoId':VIDEO,'channelId':CHANNEL,'title':'Original','description':'Old description','privacy':'VIDEO_PRIVACY_PRIVATE','draftStatus':'DRAFT_STATUS_PUBLIC',
                      'thumbnailEditorState':{'customThumbnail':{'externalImageId':'IM-old'},'defaultStill':False},'thumbnailDetails':{'thumbnails':[]}}
            def reset(locale, timezone_index=0):
                server.config={'locale':locale,'video':copy.deepcopy(baseline),'scheduled':False,'playlists':['PL-existing'],
                               'model':{'date':{'year':2099,'month':0,'day':3},'selectedTimeOfDayValue':0,'selectedTimezoneIndex':timezone_index}}
            try:
                with patch('src.studio_publishing_editor._new_driver',return_value=adapter), \
                     patch('src.studio_publishing_editor.get_channels_info',return_value=channel), \
                     patch('src.studio_publishing_editor.inject_cookies_via_cdp'), \
                     patch('src.studio_publishing_editor.close_driver'), \
                     patch('src.publishing_thumbnails.thumbnail_pixels',return_value=bytes([42])*43200):
                    for locale,timezone_index in [('vi-VN',0),('de-DE',1)]:
                        with self.subTest(locale=locale):
                            reset(locale,timezone_index)
                            reference={**REFERENCE,"description":""} if locale=='de-DE' else REFERENCE
                            verifier=ThumbnailReadback(CHANNEL,VIDEO,image,reader=lambda *_:studio_video_from_payload(server.config['video']))
                            controls=StudioThumbnailBrowser(verify_saved=verifier)
                            before=len(server.saves)
                            result=controls.publish(CHANNEL,VIDEO,image,reference,STAMP,expected_title='Original',expected_description='Old description')
                            self.assertTrue(result['verified']);self.assertEqual(len(server.saves),before+1)
                            saved=server.saves[-1]
                            self.assertEqual(saved['scheduledPublishing']['set'],{'timeSec':str(STAMP),'privacy':'PUBLIC'})
                            self.assertEqual(saved['title']['newTitle'],reference['title']);self.assertEqual(saved['description']['newDescription'],reference['description'])
                            self.assertEqual(saved['playlists'],['PL-first','PL-existing']);self.assertNotIn('PUBLIC_NOW',saved['actions'])
                            order=[saved['actions'].index(name) for name in ['thumbnail','title','description','playlist','playlist_done','schedule','schedule_done','save']]
                            self.assertEqual(order,sorted(order))
                            self.assertEqual(server.config['video']['draftStatus'],'DRAFT_STATUS_PUBLIC')
                            again=controls.publish(CHANNEL,VIDEO,image,reference,STAMP,expected_title='Original',expected_description='Old description',thumbnail_uploaded=True)
                            self.assertTrue(again['verified']);self.assertEqual(len(server.saves),before+1)
                    reset('en-US');server.config['video']['title']='Manual change'
                    before=len(server.saves)
                    with self.assertRaisesRegex(PublishingBrowserError,'được sửa khác'):
                        controls.publish(CHANNEL,VIDEO,image,REFERENCE,STAMP,expected_title='Original',expected_description='Old description',thumbnail_uploaded=True)
                    self.assertEqual(len(server.saves),before)
                    reset('en-US');server.reject=True
                    verifier=ThumbnailReadback(CHANNEL,VIDEO,image,reader=lambda *_:studio_video_from_payload(server.config['video']))
                    with self.assertRaisesRegex(PublishingBrowserError,'YouTube báo lỗi'):
                        StudioThumbnailBrowser(verify_saved=verifier).publish(CHANNEL,VIDEO,image,REFERENCE,STAMP,expected_title='Original',expected_description='Old description')
                    self.assertEqual(len(server.saves),before+1);self.assertFalse(server.config['scheduled'])
            finally:
                driver.quit();server.shutdown();server.server_close();worker.join(5)


if __name__=='__main__':
    unittest.main()
