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
from src.studio_publishing_editor import StudioPublishingEditor, _parse_timezone_offset, set_text
from tests.test_studio_publishing_integration import PAGE, CHANNEL, VIDEO, LocalStudioDriver

STAMP = 4071034800  # 2099-01-02 18:00 UTC+7
REFERENCE = {"title":"เพลงใหม่ 🎵 | Música", "description":"Dòng đầu 🎶\n\n00:00 Canção de Fé\n#Música\n"}
MULTILINE_NO_TRAILING_NL = {
    "title": "TRỰC TIẾP | BÁN KẾT 1 | ZHAO JIAN BO VS DAI YONG",
    "description": "Dòng 1 🎱\n\nDòng 2   https://example.com\n  ▶️ Fanpage: test\n   ☞ Do not Reup",
}
FIELDS = '''<div id="title-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
<div id="description-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
<ytkc-made-for-kids-select>
 <div class="made-for-kids-rating-container">
  <tp-yt-paper-radio-group role="radiogroup">
   <tp-yt-paper-radio-button name="VIDEO_MADE_FOR_KIDS_MFK" role="radio" aria-checked="false" style="display:block">Có, nội dung này dành cho trẻ em</tp-yt-paper-radio-button>
   <tp-yt-paper-radio-button name="VIDEO_MADE_FOR_KIDS_NOT_MFK" role="radio" aria-checked="false" style="display:block">Không, nội dung này không dành cho trẻ em</tp-yt-paper-radio-button>
  </tp-yt-paper-radio-group>
 </div>
</ytkc-made-for-kids-select>'''
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
 <ytcp-stepper id="ytcp-uploads-dialog-stepper">
  <button id="step-badge-0" test-id="DETAILS" aria-selected="true" active>Details</button>
  <button id="step-badge-1" test-id="RIGHTS_MANAGEMENT" style="display:none">Quản lý quyền</button>
  <button id="step-badge-2" test-id="MONETIZATION" style="display:none">Kiếm tiền</button>
  <button id="step-badge-content" test-id="CONTENT_RATINGS" style="display:none">Mức độ phù hợp</button>
  <button id="step-badge-elements" test-id="VIDEO_ELEMENTS" style="display:none">Video elements</button>
  <button id="step-badge-checks" test-id="CHECKS" style="display:none">Checks</button>
  <button id="step-badge-3" test-id="REVIEW">Sichtbarkeit</button>
 </ytcp-stepper>
 <div id="draft-details-panel">
  <div id="title-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
  <div id="description-textarea"><div id="textbox" contenteditable="true" role="textbox" style="white-space:pre-wrap"></div></div>
  <ytcp-thumbnail-editor><input type="file" accept="image/jpeg" hidden></ytcp-thumbnail-editor>
  <ytcp-video-metadata-playlists><ytcp-dropdown-trigger role="button" style="display:block">Playlists</ytcp-dropdown-trigger></ytcp-video-metadata-playlists>
  <ytkc-made-for-kids-select>
   <div class="made-for-kids-rating-container">
    <tp-yt-paper-radio-group role="radiogroup">
     <tp-yt-paper-radio-button name="VIDEO_MADE_FOR_KIDS_MFK" role="radio" aria-checked="false" style="display:block">Có, nội dung này dành cho trẻ em</tp-yt-paper-radio-button>
     <tp-yt-paper-radio-button name="VIDEO_MADE_FOR_KIDS_NOT_MFK" role="radio" aria-checked="false" style="display:block">Không, nội dung này không dành cho trẻ em</tp-yt-paper-radio-button>
    </tp-yt-paper-radio-group>
   </div>
  </ytkc-made-for-kids-select>
 </div>
 <ytcms-video-rights-management-settings style="display:none">
  <ytcms-policy-select class="upload-policy-select">
   <ytcp-dropdown-trigger role="button" style="display:block"><span class="dropdown-trigger-text">Track in all countries</span></ytcp-dropdown-trigger>
  </ytcms-policy-select>
  <ytcms-asset-ownership-territory>
   <tp-yt-paper-radio-group id="ownership-group">
    <tp-yt-paper-radio-button id="global-radio-button" name="GLOBAL" role="radio" aria-checked="false" style="display:block">Toàn cầu</tp-yt-paper-radio-button>
    <tp-yt-paper-radio-button id="specific-radio-button" name="SPECIFIC" role="radio" aria-checked="true" style="display:block">Các lãnh thổ cụ thể</tp-yt-paper-radio-button>
   </tp-yt-paper-radio-group>
  </ytcms-asset-ownership-territory>
  <div id="metadata-music-video-song-input"><textarea></textarea></div>
  <ytcms-identified-people-editor>
   <ytcp-chip-bar><div class="chip-and-bar"><input id="text-input" type="text"></div></ytcp-chip-bar>
  </ytcms-identified-people-editor>
 </ytcms-video-rights-management-settings>
 <ytcp-uploads-monetization style="display:none">
  <ytpp-video-monetization-basics>
   <div id="monetization-ineligible-notice" style="display:none">Video này không đủ điều kiện kiếm tiền do xác nhận quyền sở hữu bản quyền.</div>
   <ytcp-dropdown-trigger id="monetization-trigger" role="button" style="display:none"><span class="dropdown-trigger-text">Chọn</span></ytcp-dropdown-trigger>
   <ytpp-ad-options-settings style="display:none">Hiện quảng cáo trong video của tôi</ytpp-ad-options-settings>
  </ytpp-video-monetization-basics>
 </ytcp-uploads-monetization>
 <ytcp-uploads-content-ratings style="display:none">
  <ytpp-self-certification-questionnaire>
   <ytcp-banner><ytcp-button id="action-1"><button>Tìm hiểu thêm</button></ytcp-button><ytcp-button id="action-2"><button>Bỏ qua</button></ytcp-button></ytcp-banner>
   <ytpp-self-certification-question><ytcp-checkbox-lit class="question-box"><div role="checkbox" aria-checked="false">Có nội dung nhạy cảm</div></ytcp-checkbox-lit></ytpp-self-certification-question>
   <ytcp-checkbox-lit class="all-none-checkbox" style="display:block"><div id="checkbox" role="checkbox" aria-checked="false">None of the above</div></ytcp-checkbox-lit>
   <ytcp-button id="submit-questionnaire-button"><ytcp-button-shape><button>Submit rating</button></ytcp-button-shape></ytcp-button>
  </ytpp-self-certification-questionnaire>
 </ytcp-uploads-content-ratings>
 <div id="draft-elements-panel" style="display:none">Video elements</div>
 <div id="draft-checks-panel" style="display:none">Checks ok</div>
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
 <ytcp-button id="next-button" style="display:none" aria-disabled="false"><ytcp-button-shape><button>Tiếp</button></ytcp-button-shape></ytcp-button>
 <ytcp-button id="done-button" aria-disabled="false"><ytcp-button-shape><button>Veröffentlichungszeitpunkt festlegen</button></ytcp-button-shape></ytcp-button>
</ytcp-uploads-dialog>
<tp-yt-paper-dialog aria-label="policy-dialog" style="display:none;position:fixed;inset:12%;background:white;z-index:2204">
 <input id="policy-filter-input" type="text">
 <div id="items" role="listbox">
  <tp-yt-paper-item id="item-0" role="option" aria-selected="false" style="display:block"><span class="title">Block in all countries</span></tp-yt-paper-item>
  <tp-yt-paper-item id="item-9" role="option" aria-selected="false" style="display:block"><span class="title">Monetize in all countries</span></tp-yt-paper-item>
  <tp-yt-paper-item id="item-10" role="option" aria-selected="true" selected style="display:block"><span class="title">Track in all countries</span></tp-yt-paper-item>
 </div>
 <ytcp-button id="apply-policy"><ytcp-button-shape><button>Áp dụng</button></ytcp-button-shape></ytcp-button>
</tp-yt-paper-dialog>
<ytcp-video-monetization-edit-dialog style="display:none;position:fixed;inset:20%;background:white;z-index:2204">
 <tp-yt-paper-radio-group>
  <tp-yt-paper-radio-button id="radio-on" name="ON" role="radio" aria-checked="false" style="display:block">Bật</tp-yt-paper-radio-button>
  <tp-yt-paper-radio-button id="radio-off" name="OFF" role="radio" aria-checked="true" style="display:block">Tắt</tp-yt-paper-radio-button>
 </tp-yt-paper-radio-group>
 <ytcp-button id="save-button"><ytcp-button-shape><button>Xong</button></ytcp-button-shape></ytcp-button>
</ytcp-video-monetization-edit-dialog>
<ytcp-dialog aria-labelledby="cms-identified-people-edit-dialog-title" style="display:none;position:fixed;inset:22%;background:white;z-index:2205">
 <div id="name-input"><textarea></textarea></div>
 <ytcp-button id="save"><ytcp-button-shape><button>Lưu</button></ytcp-button-shape></ytcp-button>
</ytcp-dialog>
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
 if(!config.hide_draft_banner){draftBanner.style.display='block';}
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
for(const host of document.querySelectorAll('#playlists-list ytcp-checkbox-lit')){const handler=host.onclick;host.onclick=event=>{handler(event);actions.push('playlist');};}
document.querySelector('.done-button button').addEventListener('click',()=>actions.push('playlist_done'));
let madeForKids=(config.made_for_kids===undefined)?'VIDEO_MADE_FOR_KIDS_NOT_MFK':(config.made_for_kids||'');
const mfkSelect=activeScope.querySelector('ytkc-made-for-kids-select');
const mfkContainer=mfkSelect?mfkSelect.querySelector('.made-for-kids-rating-container'):null;
const mfkRadios=mfkSelect?Array.from(mfkSelect.querySelectorAll('tp-yt-paper-radio-button')):[];
let syncStepperHook=null;
function syncMfk(){
 if(!mfkContainer)return;
 if(madeForKids)mfkContainer.removeAttribute('has-error');
 else mfkContainer.setAttribute('has-error','Bạn cần phải trả lời câu hỏi này');
 for(const r of mfkRadios){
  r.setAttribute('aria-checked',r.getAttribute('name')===madeForKids?'true':'false');
 }
}
syncMfk();
for(const r of mfkRadios){
 r.onclick=()=>{
  madeForKids=r.getAttribute('name')||'';
  syncMfk();
  actions.push(madeForKids==='VIDEO_MADE_FOR_KIDS_NOT_MFK'?'audience_not_mfk':'audience_mfk');
  if(!isDraft)setSaveEnabled(true);
  else if(syncStepperHook)syncStepperHook();
 };
}
if(!isDraft){
 document.querySelector('ytcp-video-metadata-visibility #select-button').onclick=()=>{baselineModel=JSON.parse(JSON.stringify(scheduler.model));working=draftScheduled;render();popupEnabled(false);visibilityPanel.style.display='block';};
} else {
 draftBanner.querySelector('#action-1 button').onclick=()=>{uploadsDialog.style.display='block';actions.push('open_draft');};
 const draftMode=config.draft_mode||'basic';
 const stepTabs={
  DETAILS:uploadsDialog.querySelector("[test-id='DETAILS']"),
  RIGHTS_MANAGEMENT:uploadsDialog.querySelector("[test-id='RIGHTS_MANAGEMENT']"),
  MONETIZATION:uploadsDialog.querySelector("[test-id='MONETIZATION']"),
  CONTENT_RATINGS:uploadsDialog.querySelector("[test-id='CONTENT_RATINGS']"),
  VIDEO_ELEMENTS:uploadsDialog.querySelector("[test-id='VIDEO_ELEMENTS']"),
  CHECKS:uploadsDialog.querySelector("[test-id='CHECKS']"),
  REVIEW:uploadsDialog.querySelector("[test-id='REVIEW']"),
 };
 const stepPanels={
  DETAILS:uploadsDialog.querySelector('#draft-details-panel'),
  RIGHTS_MANAGEMENT:uploadsDialog.querySelector('ytcms-video-rights-management-settings'),
  MONETIZATION:uploadsDialog.querySelector('ytcp-uploads-monetization'),
  CONTENT_RATINGS:uploadsDialog.querySelector('ytcp-uploads-content-ratings'),
  VIDEO_ELEMENTS:uploadsDialog.querySelector('#draft-elements-panel'),
  CHECKS:uploadsDialog.querySelector('#draft-checks-panel'),
  REVIEW:uploadsDialog.querySelector('#draft-review-panel'),
 };
 const nextHost=uploadsDialog.querySelector('#next-button'), nextBtn=nextHost.querySelector('button');
 const doneHost=uploadsDialog.querySelector('#done-button'), doneBtn=doneHost.querySelector('button');
 let activeStep='DETAILS';
 let policyValue='Track in all countries', ownershipGlobal=false, artistChipDone=false;
 let monetizationOn=false, ratingsCompleted=false;
 let visibleSteps=['DETAILS','REVIEW'];
 if(draftMode==='monetized'){
  visibleSteps=['DETAILS','MONETIZATION','VIDEO_ELEMENTS','CHECKS','REVIEW'];
 } else if(draftMode==='monetized_ineligible'){
  visibleSteps=['DETAILS','MONETIZATION','VIDEO_ELEMENTS','CHECKS','REVIEW'];
 } else if(draftMode==='cms'){
  visibleSteps=['DETAILS','RIGHTS_MANAGEMENT','VIDEO_ELEMENTS','CHECKS','REVIEW'];
 }
 function rightsComplete(){return policyValue==='Monetize in all countries' && ownershipGlobal && artistChipDone;}
 function draftReadyToPublish(){
  if(!madeForKids)return false;
  if(draftMode==='monetized')return monetizationOn && ratingsCompleted;
  if(draftMode==='cms')return rightsComplete() && monetizationOn;
  return true;
 }
 function syncStepper(){
  Object.entries(stepTabs).forEach(([id,tab])=>{
   const shown=visibleSteps.includes(id);
   tab.style.display=shown?'':'none';
   tab.setAttribute('aria-selected',id===activeStep?'true':'false');
   if(id===activeStep)tab.setAttribute('active','');else tab.removeAttribute('active');
   // Deliberately shift step-badge-3 to VIDEO_ELEMENTS/CHECKS on 5-6 step wizards!
   if(shown){
    const idx=visibleSteps.indexOf(id);
    if(idx===3 && id!=='REVIEW')tab.id='step-badge-3';
    else if(id==='REVIEW')tab.id='step-badge-'+idx;
   }
  });
  Object.entries(stepPanels).forEach(([id,panel])=>{panel.style.display=(id===activeStep)?'block':'none';});
  const isReview=activeStep==='REVIEW';
  nextHost.style.display=isReview?'none':'';
  const nextBlocked=(activeStep==='DETAILS' && !madeForKids) || (activeStep==='RIGHTS_MANAGEMENT' && !rightsComplete()) || (activeStep==='CONTENT_RATINGS' && !ratingsCompleted);
  nextBtn.disabled=nextBlocked;nextHost.setAttribute('aria-disabled',nextBlocked?'true':'false');
  const doneDisabled=!draftReadyToPublish();
  doneBtn.disabled=doneDisabled;doneHost.setAttribute('aria-disabled',doneDisabled?'true':'false');
  if(activeStep==='REVIEW'){working=draftScheduled;render();}
 }
 syncStepperHook=syncStepper;
 function goStep(id){
  if(!visibleSteps.includes(id))return;
  activeStep=id;
  syncStepper();
 }
 Object.entries(stepTabs).forEach(([id,tab])=>{tab.onclick=()=>goStep(id);});
 nextBtn.onclick=()=>{
  const idx=visibleSteps.indexOf(activeStep);
  if(idx>=0 && idx+1<visibleSteps.length)goStep(visibleSteps[idx+1]);
 };
 if(draftMode==='monetized'){
  const monTrigger=stepPanels.MONETIZATION.querySelector('#monetization-trigger');
  const adOptions=stepPanels.MONETIZATION.querySelector('ytpp-ad-options-settings');
  const monDialog=document.querySelector('ytcp-video-monetization-edit-dialog');
  monTrigger.style.display='flex';
  monTrigger.onclick=()=>{monDialog.style.display='block';actions.push('monetization_open');};
  const rOn=monDialog.querySelector('#radio-on'), rOff=monDialog.querySelector('#radio-off');
  rOn.onclick=()=>{rOn.setAttribute('aria-checked','true');rOff.setAttribute('aria-checked','false');actions.push('monetization_on');};
  monDialog.querySelector('#save-button button').onclick=()=>{
   monDialog.style.display='none';monetizationOn=true;
   monTrigger.querySelector('.dropdown-trigger-text').innerText='Bật';
   adOptions.style.display='block';
   if(!visibleSteps.includes('CONTENT_RATINGS')){
    visibleSteps=['DETAILS','MONETIZATION','CONTENT_RATINGS','VIDEO_ELEMENTS','CHECKS','REVIEW'];
   }
   actions.push('monetization_done');syncStepper();
  };
  stepPanels.CONTENT_RATINGS.querySelectorAll('ytcp-banner button').forEach(b=>{b.onclick=()=>actions.push('banner_action');});
  const noneBox=stepPanels.CONTENT_RATINGS.querySelector('.all-none-checkbox');
  noneBox.onclick=()=>{noneBox.querySelector('[role=checkbox]').setAttribute('aria-checked','true');actions.push('content_ratings_none');};
  stepPanels.CONTENT_RATINGS.querySelector('#submit-questionnaire-button button').onclick=()=>{
   if(noneBox.querySelector('[role=checkbox]').getAttribute('aria-checked')!=='true')return;
   ratingsCompleted=true;stepTabs.CONTENT_RATINGS.setAttribute('state','completed');
   actions.push('content_ratings_submit');syncStepper();
  };
 } else if(draftMode==='monetized_ineligible'){
  stepPanels.MONETIZATION.querySelector('#monetization-ineligible-notice').style.display='block';
 } else if(draftMode==='cms'){
  const policyDialog=document.querySelector('tp-yt-paper-dialog[aria-label="policy-dialog"]');
  const policyTrigger=stepPanels.RIGHTS_MANAGEMENT.querySelector('ytcms-policy-select ytcp-dropdown-trigger');
  const filterInput=policyDialog.querySelector('#policy-filter-input');
  let pendingPolicy=policyValue;
  policyTrigger.onclick=()=>{policyDialog.style.display='block';filterInput.value='';actions.push('policy_open');};
  filterInput.oninput=()=>{
   const q=filterInput.value.trim().toLowerCase();
   policyDialog.querySelectorAll('tp-yt-paper-item').forEach(it=>{
    const txt=it.querySelector('.title').innerText.toLowerCase();
    it.style.display=(!q || txt.includes(q))?'block':'none';
   });
   actions.push('policy_filter');
  };
  policyDialog.querySelectorAll('tp-yt-paper-item').forEach(it=>{
   it.onclick=()=>{
    policyDialog.querySelectorAll('tp-yt-paper-item').forEach(x=>{x.setAttribute('aria-selected','false');x.removeAttribute('selected');});
    it.setAttribute('aria-selected','true');it.setAttribute('selected','');
    pendingPolicy=it.querySelector('.title').innerText.trim();
    actions.push('policy_select');
   };
  });
  policyDialog.querySelector('#apply-policy button').onclick=()=>{
   policyValue=pendingPolicy;
   policyTrigger.querySelector('.dropdown-trigger-text').innerText=policyValue;
   policyDialog.style.display='none';
   if(policyValue==='Monetize in all countries'){
    monetizationOn=true;
    stepPanels.MONETIZATION.querySelector('ytpp-ad-options-settings').style.display='block';
    if(!visibleSteps.includes('MONETIZATION')){
     visibleSteps=['DETAILS','RIGHTS_MANAGEMENT','MONETIZATION','VIDEO_ELEMENTS','CHECKS','REVIEW'];
    }
   }
   actions.push('policy_apply');syncStepper();
  };
  const gRadio=stepPanels.RIGHTS_MANAGEMENT.querySelector('#global-radio-button');
  const sRadio=stepPanels.RIGHTS_MANAGEMENT.querySelector('#specific-radio-button');
  gRadio.onclick=()=>{gRadio.setAttribute('aria-checked','true');sRadio.setAttribute('aria-checked','false');ownershipGlobal=true;actions.push('ownership_global');syncStepper();};
  const artistBar=stepPanels.RIGHTS_MANAGEMENT.querySelector('ytcms-identified-people-editor .chip-and-bar');
  const artistInput=artistBar.querySelector('#text-input');
  const artistDialog=document.querySelector('ytcp-dialog[aria-labelledby="cms-identified-people-edit-dialog-title"]');
  const artistName=artistDialog.querySelector('#name-input textarea');
  artistInput.onkeydown=ev=>{
   if(ev.key!=='Enter')return;
   ev.preventDefault();
   artistName.value=artistInput.value.trim();artistInput.value='';
   artistDialog.style.display='block';actions.push('artist_popup_open');
  };
  artistDialog.querySelector('#save button').onclick=()=>{
   const name=artistName.value.trim();if(!name)return;
   const chip=document.createElement('ytcp-chip');chip.innerText=name;artistBar.prepend(chip);
   artistDialog.style.display='none';artistChipDone=true;actions.push('artist_popup_save');syncStepper();
  };
 }
 syncStepper();
 if(config.auto_open_draft){uploadsDialog.style.display='block';goStep('REVIEW');}
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
 const body={encryptedVideoId:config.video.videoId,nativeEditorCommit:true,actions,madeForKids,title:{newTitle:title.innerText},description:{newDescription:descriptionValue},
  playlists:Array.from(document.querySelectorAll('#playlists-list ytcp-checkbox-lit')).filter(e=>e.querySelector('[role=checkbox]').getAttribute('aria-checked')==='true').map(e=>e.getAttribute('test-id')),
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
        if '/videos/upload' in self.path and 'd=ud' in self.path and f'udvid={VIDEO}' in self.path:
            config['auto_open_draft']=True
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
                if not payload.get('madeForKids'):
                    raise AssertionError('Made for Kids must be selected before saving')
                config=self.server.config;video=config['video']
                video.update(title=payload['title']['newTitle'],description=payload['description']['newDescription'])
                if 'thumbnail' in payload:video['thumbnailEditorState']={'customThumbnail':{'externalImageId':'IM-new'},'defaultStill':False,'stillId':0}
                video['scheduledPublishingDetails']={'publishTimeSeconds':payload['scheduledPublishing']['set']['timeSec']}
                # Deliberately retain the stale draft enum that broke API-only
                # confirmation, while the persisted Studio UI is Scheduled.
                video['draftStatus']='DRAFT_STATUS_PUBLIC'
                config.update(model=payload['model'],scheduled=True,draft=False,playlists=payload['playlists'],made_for_kids=payload['madeForKids'])
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

    def test_complete_content_ratings_skips_already_completed_step(self):
        driver = Mock()
        dialog = Mock()
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        with patch.object(editor, "_draft_step_state", return_value="completed") as state_fn:
            editor._complete_content_ratings(driver, dialog)
        state_fn.assert_called_once_with(dialog, "CONTENT_RATINGS")
        driver.execute_script.assert_not_called()

    def test_parse_timezone_offset_handles_bidi_arabic_and_short_gmt(self):
        for note, expected in (
            ("Local time (GMT+0700)", 420),
            ("(غرينتش\u200e+07:00)", 420),
            ("(GMT+7)", 420),
            ("(GMT+٠٧:٠٠)", 420),
            ("Pacific (GMT\u221208:00)", -480),
        ):
            with self.subTest(note=note):
                self.assertEqual(_parse_timezone_offset(note), expected)

    def test_inspect_schedules_records_per_video_error_without_name_error_and_continues(self):
        driver = Mock()
        driver.window_handles = ["h1"]
        channel = SimpleNamespace(id=CHANNEL, cookies=[])
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        good = {"source": "studio_ui", "channel_id": CHANNEL, "video_id": "VideoTwo___", "scheduled": False, "publish_at": None}
        with patch("src.studio_publishing_editor.get_channels_info", return_value=channel), \
                patch("src.studio_publishing_editor._new_driver", return_value=driver), \
                patch("src.studio_publishing_editor.inject_cookies_via_cdp"), \
                patch("src.studio_publishing_editor.close_driver"), \
                patch.object(editor, "_inspect_schedule_in_driver", side_effect=[PublishingBrowserError("missing control"), good]):
            results = editor.inspect_schedules(CHANNEL, [VIDEO, "VideoTwo___"])
        self.assertIsInstance(results[VIDEO], PublishingBrowserError)
        self.assertEqual(results["VideoTwo___"], good)

    def test_ensure_audience_selected_skips_when_widget_absent(self):
        driver = Mock()
        scope = Mock()
        scope.find_elements.return_value = []
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        with patch("src.studio_publishing_editor.visible", return_value=None):
            self.assertFalse(editor._ensure_audience_selected(driver, scope))

    def test_ensure_audience_selected_skips_when_already_checked(self):
        driver = Mock()
        scope = Mock()
        host = Mock()
        r_yes = Mock(is_displayed=Mock(return_value=True))
        r_yes.get_attribute.side_effect = lambda attr: "true" if attr == "aria-checked" else None
        r_no = Mock(is_displayed=Mock(return_value=True))
        r_no.get_attribute.side_effect = lambda attr: "false" if attr == "aria-checked" else None
        host.find_elements.return_value = [r_yes, r_no]
        controls = StudioThumbnailBrowser()
        controls._click_control = Mock()
        editor = StudioPublishingEditor(controls)
        with patch("src.studio_publishing_editor.visible", return_value=host):
            self.assertFalse(editor._ensure_audience_selected(driver, scope))
        controls._click_control.assert_not_called()

    def test_ensure_audience_selected_selects_not_mfk_when_unanswered(self):
        driver = Mock()
        scope = Mock()
        host = Mock()
        r_yes = Mock(is_displayed=Mock(return_value=True))
        r_yes.get_attribute.side_effect = lambda attr: "false" if attr == "aria-checked" else None
        not_mfk_state = {"checked": "false"}
        r_no = Mock(is_displayed=Mock(return_value=True))
        r_no.get_attribute.side_effect = lambda attr: not_mfk_state["checked"] if attr == "aria-checked" else None
        host.find_elements.return_value = [r_yes, r_no]
        controls = StudioThumbnailBrowser()
        controls._click_control = Mock(side_effect=lambda *args, **kwargs: not_mfk_state.__setitem__("checked", "true"))
        editor = StudioPublishingEditor(controls)
        progress = []

        def fake_visible(node, selector):
            if node is scope and selector == "ytkc-made-for-kids-select":
                return host
            if node is scope and "VIDEO_MADE_FOR_KIDS_NOT_MFK" in selector:
                return r_no
            return None

        with patch("src.studio_publishing_editor.visible", side_effect=fake_visible):
            changed = editor._ensure_audience_selected(
                driver,
                scope,
                on_progress=lambda step, message: progress.append((step, message)),
            )
        self.assertTrue(changed)
        controls._click_control.assert_called_once()
        self.assertEqual(progress[0][0], "audience")

    def test_complete_monetization_passes_locked_trigger_when_next_enabled(self):
        driver = Mock()
        dialog = Mock()
        panel = Mock(text="Kiếm tiền bị tắt cho video này")
        trigger = Mock()
        trigger.is_enabled.return_value = True
        trigger.get_attribute.side_effect = lambda attr: "true" if attr == "aria-disabled" else None
        next_btn = Mock()
        controls = StudioThumbnailBrowser()
        controls._click_control = Mock()
        controls._button_control = Mock(side_effect=lambda scope, sel: next_btn if sel == "#next-button" else None)
        editor = StudioPublishingEditor(controls)

        def fake_visible(scope, selector):
            if scope is dialog and selector == "ytcp-uploads-monetization":
                return panel
            if scope is panel and selector == "ytcp-dropdown-trigger":
                return trigger
            return None

        with patch("src.studio_publishing_editor.visible", side_effect=fake_visible):
            editor._complete_monetization(driver, dialog)
        controls._click_control.assert_not_called()

    def test_complete_monetization_passes_ineligible_panel_without_trigger_when_next_enabled(self):
        driver = Mock()
        dialog = Mock()
        panel = Mock(text="Video này không đủ điều kiện kiếm tiền do xác nhận quyền sở hữu bản quyền.")
        next_btn = Mock()
        controls = StudioThumbnailBrowser()
        controls._click_control = Mock()
        controls._button_control = Mock(side_effect=lambda scope, sel: next_btn if sel == "#next-button" else None)
        editor = StudioPublishingEditor(controls)

        def fake_visible(scope, selector):
            if scope is dialog and selector == "ytcp-uploads-monetization":
                return panel
            return None

        with patch.object(StudioPublishingEditor, "MONETIZATION_CONTROLS_GRACE_SECONDS", 0.0), \
                patch("src.studio_publishing_editor.visible", side_effect=fake_visible):
            editor._complete_monetization(driver, dialog)
        controls._click_control.assert_not_called()

    def test_editor_mode_detects_draft_without_banner_via_draft_status(self):
        driver = Mock()
        driver.find_elements.return_value = []
        driver.execute_script.return_value = {
            "hasVisibility": False,
            "draftStatus": "DRAFT_STATUS_PUBLIC",
            "isDraft": False,
            "hasSidepanel": True,
        }
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        with patch("src.studio_publishing_editor.visible", return_value=None):
            self.assertEqual(editor._editor_mode(driver), "draft")

    def test_editor_mode_does_not_treat_draft_status_none_as_draft(self):
        driver = Mock()
        driver.find_elements.return_value = []
        driver.execute_script.return_value = {
            "hasVisibility": False,
            "draftStatus": "DRAFT_STATUS_NONE",
            "isDraft": False,
            "hasSidepanel": True,
        }
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        with patch("src.studio_publishing_editor.visible", return_value=None):
            self.assertIsNone(editor._editor_mode(driver, allow_bannerless_draft=True))

    def test_editor_mode_scrolls_visibility_container_into_view(self):
        driver = Mock()
        vis_node = Mock()
        vis_node.is_displayed.side_effect = [False, True]
        driver.find_elements.side_effect = lambda _by, sel: [vis_node] if sel == "ytcp-video-metadata-visibility #container" else []
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        with patch("src.studio_publishing_editor.visible", return_value=None):
            self.assertEqual(editor._editor_mode(driver), "standard")
        driver.execute_script.assert_called_once()

    def test_open_draft_dialog_falls_back_to_direct_upload_popup_url(self):
        driver = Mock()
        driver.current_url = f"https://studio.youtube.com/channel/{CHANNEL}/videos/upload?d=ud&udvid={VIDEO}&hl=en"
        dialog = Mock()
        title_node = Mock()
        desc_node = Mock()
        dialog.get_attribute.side_effect = lambda attr: VIDEO if attr == "video-id" else None
        controls = StudioThumbnailBrowser()
        controls._button_control = Mock(return_value=None)
        editor = StudioPublishingEditor(controls)

        def fake_visible(scope, selector):
            if scope is driver and selector == "ytcp-uploads-dialog":
                return dialog if driver.get.called else None
            if scope is dialog:
                return title_node if selector else None
            return None

        with patch("src.studio_publishing_editor.visible", side_effect=fake_visible):
            result = editor._open_draft_dialog(driver, VIDEO, channel_id=CHANNEL)
        self.assertIs(result, dialog)
        driver.get.assert_called_once_with(
            f"https://studio.youtube.com/channel/{CHANNEL}/videos/upload?d=ud&udvid={VIDEO}&hl=en"
        )


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
            def reset(locale, timezone_index=0, draft=False, draft_mode='basic', made_for_kids='VIDEO_MADE_FOR_KIDS_NOT_MFK', hide_draft_banner=False):
                server.config={'locale':locale,'video':copy.deepcopy(baseline),'scheduled':False,'draft':draft,'draft_mode':draft_mode,'made_for_kids':made_for_kids,'hide_draft_banner':hide_draft_banner,'playlists':['PL-existing'],
                               'model':{'date':{'year':2099,'month':0,'day':3},'selectedTimeOfDayValue':0,'selectedTimezoneIndex':timezone_index}}
            try:
                with patch('src.studio_publishing_editor._new_driver',return_value=adapter), \
                     patch('src.studio_publishing_editor.get_channels_info',return_value=channel), \
                     patch('src.studio_publishing_editor.inject_cookies_via_cdp'), \
                     patch('src.studio_publishing_editor.close_driver'), \
                     patch('src.publishing_thumbnails.thumbnail_pixels',return_value=bytes([42])*43200):
                    for label,locale,timezone_index,draft,draft_mode,made_for_kids,hide_draft_banner,reference in [
                        ('vi-standard','vi-VN',0,False,'basic','VIDEO_MADE_FOR_KIDS_NOT_MFK',False,REFERENCE),
                        ('vi-standard-unanswered-mfk','vi-VN',0,False,'basic','',False,REFERENCE),
                        ('de-empty','de-DE',1,False,'basic','VIDEO_MADE_FOR_KIDS_NOT_MFK',False,{**REFERENCE,'description':''}),
                        ('vi-multiline-no-trailing-nl','vi-VN',0,False,'basic','VIDEO_MADE_FOR_KIDS_NOT_MFK',False,MULTILINE_NO_TRAILING_NL),
                        ('de-draft-dialog','de-DE',1,True,'basic','VIDEO_MADE_FOR_KIDS_NOT_MFK',False,MULTILINE_NO_TRAILING_NL),
                        ('vi-draft-preserves-existing-mfk','vi-VN',0,True,'basic','VIDEO_MADE_FOR_KIDS_MFK',False,REFERENCE),
                        ('vi-ypp-monetized-draft','vi-VN',0,True,'monetized','VIDEO_MADE_FOR_KIDS_NOT_MFK',False,MULTILINE_NO_TRAILING_NL),
                        ('vi-claimed-unanswered-mfk-draft','vi-VN',0,True,'monetized_ineligible','',False,MULTILINE_NO_TRAILING_NL),
                        ('vi-cms-rights-draft','vi-VN',0,True,'cms','VIDEO_MADE_FOR_KIDS_NOT_MFK',False,MULTILINE_NO_TRAILING_NL),
                        ('vi-draft-direct-popup-fallback','vi-VN',0,True,'monetized_ineligible','',True,MULTILINE_NO_TRAILING_NL),
                    ]:
                        with self.subTest(case=label):
                            reset(locale,timezone_index,draft=draft,draft_mode=draft_mode,made_for_kids=made_for_kids,hide_draft_banner=hide_draft_banner)
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
                            self.assertNotIn('banner_action',saved['actions'])
                            expected_mfk = made_for_kids or 'VIDEO_MADE_FOR_KIDS_NOT_MFK'
                            self.assertEqual(saved['madeForKids'], expected_mfk)
                            if made_for_kids:
                                self.assertNotIn('audience_not_mfk', saved['actions'])
                            if draft_mode=='monetized':
                                expected_order=['open_draft','thumbnail','title','description','playlist','playlist_done','monetization_open','monetization_on','monetization_done','content_ratings_none','content_ratings_submit','schedule','save']
                            elif draft_mode=='monetized_ineligible' and hide_draft_banner:
                                expected_order=['thumbnail','title','description','playlist','playlist_done','audience_not_mfk','schedule','save']
                            elif draft_mode=='monetized_ineligible':
                                expected_order=['open_draft','thumbnail','title','description','playlist','playlist_done','audience_not_mfk','schedule','save']
                            elif draft_mode=='cms':
                                expected_order=['open_draft','thumbnail','title','description','playlist','playlist_done','policy_open','policy_filter','policy_select','policy_apply','ownership_global','artist_popup_open','artist_popup_save','schedule','save']
                            elif draft and not made_for_kids:
                                expected_order=['open_draft','thumbnail','title','description','playlist','playlist_done','audience_not_mfk','schedule','save']
                            elif draft:
                                expected_order=['open_draft','thumbnail','title','description','playlist','playlist_done','schedule','save']
                            elif not made_for_kids:
                                expected_order=['thumbnail','title','description','playlist','playlist_done','audience_not_mfk','schedule','schedule_done','save']
                            else:
                                expected_order=['thumbnail','title','description','playlist','playlist_done','schedule','schedule_done','save']
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

    def test_rtl_narrow_visibility_scrolls_select_button_and_opens_popup(self):
        from urllib.parse import quote
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=945,1012")
        driver = webdriver.Chrome(service=Service(os.environ["CHROMEDRIVER"]), options=options)
        editor = StudioPublishingEditor(StudioThumbnailBrowser())
        html = """<!doctype html><html dir="rtl"><body>
        <div style="width:1200px;display:flex;justify-content:flex-end;">
          <ytcp-video-metadata-visibility style="display:block;width:352px;margin-left:-191px;">
            <div id="container" style="display:flex;justify-content:space-between;width:352px;">
              <div>Visibility</div>
              <ytcp-icon-button id="select-button" role="button" tabindex="0" aria-disabled="false"
                style="display:inline-flex;width:40px;height:40px;"
                onclick="document.getElementById('popup').style.display='block';">
                <button style="width:40px;height:40px;">V</button>
              </ytcp-icon-button>
            </div>
          </ytcp-video-metadata-visibility>
        </div>
        <ytcp-video-visibility-edit-popup id="popup" style="display:none;position:fixed;inset:40px;background:white;">
          <ytcp-video-visibility-select style="display:block;width:300px;height:200px;"></ytcp-video-visibility-select>
        </ytcp-video-visibility-edit-popup></body></html>"""
        try:
            driver.get("data:text/html;charset=utf-8," + quote(html))
            select = editor._visibility(driver)
            self.assertIsNotNone(select)
            self.assertTrue(select.is_displayed())
        finally:
            driver.quit()


if __name__=='__main__':
    unittest.main()
