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
from unittest.mock import Mock, call, patch

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

from src.module.base import studio_video_from_payload
from src.publishing_browser import PublishingBrowserError, StudioThumbnailBrowser
from src.publishing_thumbnails import ThumbnailReadback
from src.studio_publishing_editor import StudioPublishingEditor, set_text
from tests.test_studio_publishing_integration import PAGE, CHANNEL, VIDEO, LocalStudioDriver

STAMP = 4071034800  # 2099-01-02 18:00 UTC+7
REFERENCE = {"title":"เพลงใหม่ 🎵 | Música", "description":"Dòng đầu 🎶\n\n00:00 Canção de Fé\n#Música\n"}
MULTILINE_NO_TRAILING_NL = {
    "title": "TRỰC TIẾP | BÁN KẾT 1 | ZHAO JIAN BO VS DAI YONG",
    "description": "Dòng 1 🎱\n\nDòng 2   https://example.com\n  ▶️ Fanpage: test\n   ☞ Do not Reup",
}
FIELDS = '''<div id="title-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
<div id="description-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>'''
EDITOR = '''
<ytcp-video-metadata-editor-sidepanel><ytcp-video-info></ytcp-video-info></ytcp-video-metadata-editor-sidepanel>
<ytcp-banner class="entity-banner opened" style="display:none"><ytcp-button id="action-1"><ytcp-button-shape><button>Entwurf bearbeiten</button></ytcp-button-shape></ytcp-button></ytcp-banner>
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
<ytcp-uploads-dialog style="display:none;position:fixed;inset:0;background:white;z-index:900">
 <button id="step-badge-0" test-id="DETAILS">Details</button>
 <button id="step-badge-3" test-id="REVIEW">Sichtbarkeit</button>
 <div id="draft-details-panel">
  <div id="title-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
  <div id="description-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
  <ytcp-thumbnail-editor><input type="file" accept="image/jpeg" hidden></ytcp-thumbnail-editor>
  <ytcp-video-metadata-playlists><ytcp-dropdown-trigger role="button" style="display:block">Playlists</ytcp-dropdown-trigger></ytcp-video-metadata-playlists>
 </div>
 <div id="draft-review-panel" style="display:none">
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
 </div>
 <ytcp-button id="done-button" aria-disabled="false"><ytcp-button-shape><button>Veröffentlichungszeitpunkt festlegen</button></ytcp-button-shape></ytcp-button>
</ytcp-uploads-dialog>
<ytcp-date-picker><div class="date-panel" style="display:none;position:fixed;inset:20%;background:white;z-index:1002"><input type="text"></div></ytcp-date-picker>
<ytcp-text-menu><div class="timezone-panel" style="display:none;position:fixed;inset:20%;background:white;z-index:1002">
<tp-yt-paper-item test-id="0" style="display:block">(GMT+0700) Local time</tp-yt-paper-item></div></ytcp-text-menu>
<script>
const config=__CONFIG__,actions=[];
const isDraft=!!config.draft;
const editorEl=document.querySelector('ytcp-video-metadata-editor');
editorEl.video=config.video;
const uploadsDialog=document.querySelector('ytcp-uploads-dialog');
uploadsDialog.setAttribute('video-id',config.video.videoId);
const activeScope=isDraft?uploadsDialog:document;
const title=activeScope.querySelector('#title-textarea #textbox'),description=activeScope.querySelector('#description-textarea #textbox');
document.querySelector('#title-textarea #textbox').innerText=config.video.title;
document.querySelector('#description-textarea #textbox').innerText=config.video.description;
title.innerText=config.video.title;description.innerText=config.video.description;
const bgTitle=document.querySelector('ytcp-video-metadata-editor #title-textarea #textbox');
const bgDesc=document.querySelector('ytcp-video-metadata-editor #description-textarea #textbox');
const visibilityHost=document.querySelector('ytcp-video-metadata-visibility');
const draftBanner=document.querySelector('ytcp-banner.entity-banner');
if(isDraft){
 visibilityHost.remove();
 draftBanner.style.display='block';
 uploadsDialog.querySelector('input[type="file"]').addEventListener('change',async()=>{
  thumbnailDirty=true;actions.push('thumbnail');
  await fetch('/youtubei/v1/video_manager/metadata_update',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({encryptedVideoId:config.video.videoId,intermediateThumb:true,thumbnail:{customThumbnail:{externalImageId:'IM-new'}}})});
 });
} else {
 file.addEventListener('change',()=>actions.push('thumbnail'));
}
const visibilityPanel=document.querySelector('.visibility-panel'),select=activeScope.querySelector('ytcp-video-visibility-select'),
 scheduler=activeScope.querySelector('ytcp-visibility-scheduler'),timeField=activeScope.querySelector('#time-of-day-container input'),
 datePanel=document.querySelector('.date-panel'),dateField=datePanel.querySelector('input'),
 timezonePanel=document.querySelector('.timezone-panel'),popupDone=document.querySelector('#save-button button'),
 badge=document.querySelector('ytcp-video-metadata-visibility #container');
let draftScheduled=config.scheduled,baselineModel,working=false;
scheduler.model=config.model;
function popupEnabled(value){popupDone.disabled=!value;popupDone.parentElement.setAttribute('aria-disabled',value?'false':'true');}
function render(){select.setAttribute('second-container-style',working?'selected':'');select.setAttribute('first-container-style',working?'':'selected');scheduler.hidden=!working;select.querySelector('#second-container-expand-button').hidden=working;timeField.value=String(Math.floor(scheduler.model.selectedTimeOfDayValue/3600)).padStart(2,'0')+':'+String(Math.floor(scheduler.model.selectedTimeOfDayValue%3600/60)).padStart(2,'0');}
if(badge){
 badge.className=config.scheduled?'schedule-icon':'private-icon';
 document.querySelector('ytcp-video-metadata-visibility #visibility-text').innerText=config.scheduled?'Scheduled':'Private';
}
for(const [node,name] of [[title,'title'],[description,'description']])node.addEventListener('input',()=>{
 // Simulate Chrome pre-wrap inserting a sentinel newline on multiline contenteditable
 actions.push(name);
 if(!isDraft)setSaveEnabled(true);
});
for(const host of document.querySelectorAll('ytcp-checkbox-lit')){const handler=host.onclick;host.onclick=event=>{handler(event);actions.push('playlist');};}
document.querySelector('.done-button button').addEventListener('click',()=>actions.push('playlist_done'));
if(!isDraft){
 document.querySelector('ytcp-video-metadata-visibility #select-button').onclick=()=>{baselineModel=JSON.parse(JSON.stringify(scheduler.model));working=draftScheduled;render();popupEnabled(false);visibilityPanel.style.display='block';};
} else {
 draftBanner.querySelector('#action-1 button').onclick=()=>{uploadsDialog.style.display='block';actions.push('open_draft');};
 uploadsDialog.querySelector('#step-badge-0').onclick=()=>{uploadsDialog.querySelector('#draft-details-panel').style.display='block';uploadsDialog.querySelector('#draft-review-panel').style.display='none';};
 uploadsDialog.querySelector('#step-badge-3').onclick=()=>{uploadsDialog.querySelector('#draft-details-panel').style.display='none';uploadsDialog.querySelector('#draft-review-panel').style.display='block';working=draftScheduled;render();};
 uploadsDialog.querySelector('ytcp-video-metadata-playlists ytcp-dropdown-trigger').onclick=()=>{panel.style.display='block';};
}
select.querySelector('[name=PUBLIC]').onclick=()=>actions.push('PUBLIC_NOW');
select.querySelector('#second-container-expand-button').onclick=()=>{working=true;render();popupEnabled(true);actions.push('schedule');};
select.querySelector('#datepicker-trigger ytcp-dropdown-trigger').onclick=()=>{
 const d=scheduler.model.date,german=document.documentElement.lang.startsWith('de');dateField.value=new Intl.DateTimeFormat(document.documentElement.lang,{year:'numeric',month:german?'2-digit':'short',day:german?'2-digit':'numeric',timeZone:'UTC'}).format(new Date(Date.UTC(d.year,d.month,d.day,12)));
 datePanel.style.display='block';dateField.focus();
};
dateField.onkeydown=event=>{if(event.key!=='Enter')return;event.preventDefault();const value=dateField.value;let parts;
 if(document.documentElement.lang.startsWith('en')){const d=new Date(value);parts={year:d.getFullYear(),month:d.getMonth(),day:d.getDate()};}
 else {const numbers=value.match(/\\d+/g).map(Number);parts={day:numbers[0],month:numbers[1]-1,year:numbers[2]};}
 scheduler.model.date=parts;datePanel.style.display='none';popupEnabled(true);actions.push('date');
};
function commitTime(){const match=timeField.value.match(/(\\d+):(\\d+)(?:\\s*([AP]M))?/i);if(!match)return;let hour=Number(match[1]);if(match[3])hour=hour%12+(match[3].toUpperCase()==='PM'?12:0);scheduler.model.selectedTimeOfDayValue=hour*3600+Number(match[2])*60;popupEnabled(true);actions.push('time');}
// Real Studio's ytcp-time-of-day-picker commits typed time on Enter, not Tab alone.
timeField.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();commitTime();}};
select.querySelector('#timezone-select-button button').onclick=()=>timezonePanel.style.display='block';
document.querySelector('tp-yt-paper-item[test-id="0"]').onclick=()=>{scheduler.model.selectedTimezoneIndex=0;timezonePanel.style.display='none';popupEnabled(true);actions.push('timezone');};
popupDone.onclick=()=>{draftScheduled=working;visibilityPanel.style.display='none';badge.className=draftScheduled?'schedule-icon':'private-icon';document.querySelector('ytcp-video-metadata-visibility #visibility-text').innerText=draftScheduled?'Scheduled':'Private';setSaveEnabled(true);actions.push('schedule_done');};
document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(datePanel.style.display!=='none')datePanel.style.display='none';else if(!isDraft){scheduler.model=JSON.parse(JSON.stringify(baselineModel));visibilityPanel.style.display='none';}}});
async function commitSave(){
 if(isDraft)draftScheduled=working;
 actions.push('save');const model=scheduler.model,d=model.date;
 const stamp=Math.floor((Date.UTC(d.year,d.month,d.day)+model.selectedTimeOfDayValue*1000-420*60000)/1000);
 const descriptionValue=description.innerHTML.toLowerCase()==='<br>'?'':(description.childNodes.length===1 && description.firstChild.nodeType===Node.TEXT_NODE?description.textContent:description.innerText);
 const body={encryptedVideoId:config.video.videoId,nativeEditorCommit:true,actions,title:{newTitle:title.innerText},description:{newDescription:descriptionValue},
  playlists:Array.from(document.querySelectorAll('ytcp-checkbox-lit')).filter(e=>e.querySelector('[role=checkbox]').getAttribute('aria-checked')==='true').map(e=>e.getAttribute('test-id')),
  scheduledPublishing:{set:{timeSec:String(stamp),privacy:'PUBLIC'}},model:JSON.parse(JSON.stringify(model)),draftScheduled};
 if(thumbnailDirty)body.thumbnail={customThumbnail:{externalImageId:'IM-new'}};
 setSaveEnabled(false);
 await fetch('/youtubei/v1/video_manager/metadata_update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
}
save.onclick=commitSave;
uploadsDialog.querySelector('#done-button button').onclick=commitSave;
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
            if payload.get('intermediateThumb'):
                response={'video':self.server.config['video']}
            elif self.server.reject:
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
                config.update(model=payload['model'],scheduled=True,draft=False,playlists=payload['playlists'])
                response={'video':video}
        data=json.dumps(response).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

    def log_message(self,*args):
        pass


class StudioEditorUnitTests(unittest.TestCase):
    def test_set_text_normalizes_prewrap_trailing_sentinel_without_source_newline(self):
        driver = Mock()
        node = Mock()
        node.get_attribute.return_value = "true"
        text = "Line 1\nLine 2"
        with patch("src.studio_publishing_editor.field_text", side_effect=["Old", text + "\n", text]):
            set_text(driver, node, text, commit=Keys.TAB)
        self.assertEqual(driver.execute_script.call_count, 2)
        self.assertIn("textContent", driver.execute_script.call_args_list[1].args[0])
        self.assertEqual(driver.execute_script.call_args_list[1].args[2], text)
        node.send_keys.assert_any_call(Keys.TAB)

    def test_set_text_rejects_genuine_mismatch_even_with_trailing_newline(self):
        driver = Mock()
        node = Mock()
        node.get_attribute.return_value = "true"
        with patch("src.studio_publishing_editor.field_text", side_effect=["Old", "Line 1\nWrong\n", "Line 1\nWrong\n"]):
            with self.assertRaises(PublishingBrowserError):
                set_text(driver, node, "Line 1\nLine 2", commit=Keys.TAB)
        self.assertEqual(driver.execute_script.call_count, 1)

    def test_set_text_sends_multiple_commit_keys_in_order(self):
        driver = Mock()
        node = Mock()
        node.get_attribute.return_value = None
        with patch("src.studio_publishing_editor.field_text", return_value="18:00"):
            set_text(driver, node, "18:00", commit=(Keys.ENTER, Keys.TAB), force=True)
        self.assertEqual(node.send_keys.call_args_list[-2:], [call(Keys.ENTER), call(Keys.TAB)])

    def test_inspect_schedule_returns_unscheduled_for_draft_banner(self):
        driver = Mock()
        channel = SimpleNamespace(id=CHANNEL, cookies=[])
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        with patch("src.studio_publishing_editor.get_channels_info", return_value=channel), \
                patch("src.studio_publishing_editor._new_driver", return_value=driver), \
                patch("src.studio_publishing_editor.inject_cookies_via_cdp"), \
                patch("src.studio_publishing_editor.close_driver"), \
                patch.object(editor, "_open"), \
                patch.object(editor, "_wait_editor_mode", return_value="draft"):
            proof = editor.inspect_schedule(CHANNEL, VIDEO)
        self.assertEqual(proof, {"source": "studio_ui", "channel_id": CHANNEL, "video_id": VIDEO, "scheduled": False, "publish_at": None})


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
            def reset(locale, timezone_index=0, draft=False):
                server.config={'locale':locale,'video':copy.deepcopy(baseline),'scheduled':False,'draft':draft,'playlists':['PL-existing'],
                               'model':{'date':{'year':2099,'month':0,'day':3},'selectedTimeOfDayValue':0,'selectedTimezoneIndex':timezone_index}}
            try:
                with patch('src.studio_publishing_editor._new_driver',return_value=adapter), \
                     patch('src.studio_publishing_editor.get_channels_info',return_value=channel), \
                     patch('src.studio_publishing_editor.inject_cookies_via_cdp'), \
                     patch('src.studio_publishing_editor.close_driver'), \
                     patch('src.publishing_thumbnails.thumbnail_pixels',return_value=bytes([42])*43200):
                    for label,locale,timezone_index,draft,reference in [
                        ('vi-standard','vi-VN',0,False,REFERENCE),
                        ('de-empty','de-DE',1,False,{**REFERENCE,'description':''}),
                        ('vi-multiline-no-trailing-nl','vi-VN',0,False,MULTILINE_NO_TRAILING_NL),
                        ('de-draft-dialog','de-DE',1,True,MULTILINE_NO_TRAILING_NL),
                    ]:
                        with self.subTest(case=label):
                            reset(locale,timezone_index,draft=draft)
                            verifier=ThumbnailReadback(CHANNEL,VIDEO,image,reader=lambda *_:studio_video_from_payload(server.config['video']))
                            controls=StudioThumbnailBrowser(verify_saved=verifier)
                            before=len(server.saves)
                            before_proof=controls.inspect_schedule(CHANNEL,VIDEO)
                            self.assertFalse(before_proof['scheduled']);self.assertIsNone(before_proof['publish_at'])
                            self.assertEqual(len(server.saves),before)
                            result=controls.publish(CHANNEL,VIDEO,image,reference,STAMP,expected_title='Original',expected_description='Old description')
                            self.assertTrue(result['verified'])
                            saved=server.saves[-1]
                            self.assertEqual(saved['scheduledPublishing']['set'],{'timeSec':str(STAMP),'privacy':'PUBLIC'})
                            self.assertEqual(saved['title']['newTitle'],reference['title']);self.assertEqual(saved['description']['newDescription'],reference['description'])
                            self.assertEqual(saved['playlists'],['PL-first','PL-existing']);self.assertNotIn('PUBLIC_NOW',saved['actions'])
                            expected_order=['open_draft','thumbnail','title','description','playlist','playlist_done','schedule','save'] if draft else ['thumbnail','title','description','playlist','playlist_done','schedule','schedule_done','save']
                            order=[saved['actions'].index(name) for name in expected_order]
                            self.assertEqual(order,sorted(order))
                            self.assertEqual(server.config['video']['draftStatus'],'DRAFT_STATUS_PUBLIC')
                            proof=controls.inspect_schedule(CHANNEL,VIDEO)
                            self.assertTrue(proof['scheduled']);self.assertEqual(proof['publish_at'],STAMP)
                            self.assertEqual(proof['video_id'],VIDEO);self.assertEqual(proof['channel_id'],CHANNEL)
                            save_count_after_publish=len(server.saves)
                            again=controls.publish(CHANNEL,VIDEO,image,reference,STAMP,expected_title='Original',expected_description='Old description',thumbnail_uploaded=True)
                            self.assertTrue(again['verified']);self.assertEqual(len(server.saves),save_count_after_publish)
                            with self.assertRaisesRegex(PublishingBrowserError,'lịch khác'):
                                controls.publish(CHANNEL,VIDEO,image,reference,STAMP+86400,expected_title='Original',expected_description='Old description',thumbnail_uploaded=True)
                            self.assertEqual(len(server.saves),save_count_after_publish)
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
