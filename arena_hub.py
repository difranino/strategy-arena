# ===================== NASDAQ STRATEGY ARENA — the game hub (HTML) =====================
import json

CSS = r"""
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
#arena{--bg:#0a0e19;--p1:#111829;--p2:#172036;--ln:#243050;--fg:#e9eefb;--mu:#8592b0;--cy:#3ef0ff;--mg:#ff3ea5;
 --gd:#ffcc33;--up:#2fe07a;--dn:#ff4d5e;background:radial-gradient(1200px 500px at 20% -10%,#1a2350 0%,var(--bg) 55%);
 color:var(--fg);font:14px/1.45 Inter,system-ui,sans-serif;padding:18px;border-radius:16px;min-height:600px;position:relative}
#arena *{box-sizing:border-box}
#arena .px{font-family:'Press Start 2P',monospace;letter-spacing:.02em}
#arena .top{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
#arena .logo{font-size:17px;line-height:1.5;background:linear-gradient(90deg,var(--cy),var(--mg));-webkit-background-clip:text;background-clip:text;color:transparent;text-shadow:0 0 18px rgba(62,240,255,.25)}
#arena .sub{color:var(--mu);font-size:12px;margin-top:4px}
#arena .pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:99px;font-size:11px;font-weight:800;letter-spacing:.06em;border:1px solid var(--ln);background:var(--p1)}
#arena .live{color:var(--up);border-color:rgba(47,224,122,.5)}
#arena .live i{width:8px;height:8px;border-radius:50%;background:var(--up);box-shadow:0 0 10px var(--up);animation:blink 1.2s infinite}
#arena .closed{color:var(--mu)}
@keyframes blink{50%{opacity:.25}}
#arena .ticker{text-align:right}
#arena .ticker b{font-size:22px;font-variant-numeric:tabular-nums}
#arena .up{color:var(--up)} #arena .dn{color:var(--dn)} #arena .mu{color:var(--mu)}
#arena .hero{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:12px;margin:16px 0}
@media(max-width:900px){#arena .hero{grid-template-columns:1fr}}
#arena .box{background:linear-gradient(180deg,var(--p2),var(--p1));border:1px solid var(--ln);border-radius:14px;padding:14px}
#arena .box h4{margin:0 0 8px;font-size:9px;color:var(--mu)}
#arena .crown{border-color:rgba(255,204,51,.6);box-shadow:0 0 0 1px rgba(255,204,51,.15),0 0 30px rgba(255,204,51,.08)}
#arena .big{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums}
#arena .nm{font-size:16px;font-weight:800}
#arena .tabs{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 14px}
#arena .tab{cursor:pointer;padding:8px 12px;border-radius:10px;border:1px solid var(--ln);background:var(--p1);color:var(--mu);font-size:9px}
#arena .tab.on{color:var(--bg);background:var(--cy);border-color:var(--cy)}
#arena .wrap{display:grid;grid-template-columns:1fr 340px;gap:14px}
@media(max-width:1000px){#arena .wrap{grid-template-columns:1fr}}
#arena .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
#arena .card{position:relative;cursor:pointer;background:linear-gradient(180deg,var(--p2),var(--p1));border:1px solid var(--ln);border-radius:14px;padding:12px;transition:transform .12s,border-color .12s}
#arena .card:hover{transform:translateY(-2px);border-color:var(--cy)}
#arena .card.danger{border-color:rgba(255,77,94,.75);animation:pulse 1.6s infinite}
@keyframes pulse{50%{box-shadow:0 0 0 3px rgba(255,77,94,.18)}}
#arena .card.lead{border-color:var(--gd)}
#arena .ch{display:flex;gap:10px;align-items:center}
#arena .av{flex:0 0 42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:12px;color:#0a0e19;font-family:'Press Start 2P',monospace}
#arena .cn{font-weight:800;font-size:13.5px;line-height:1.2;padding-right:34px}
#arena .cl{font-size:10px;color:var(--mu);letter-spacing:.08em;text-transform:uppercase;margin-top:3px}
#arena .lv{position:absolute;top:10px;right:10px;font-size:8px;color:var(--gd)}
#arena .row{display:flex;justify-content:space-between;align-items:center;margin-top:10px}
#arena .pnl{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums}
#arena .stance{font-size:10px;font-weight:800;letter-spacing:.08em;padding:4px 8px;border-radius:8px}
#arena .s-long{background:rgba(47,224,122,.15);color:var(--up)} #arena .s-short{background:rgba(255,77,94,.15);color:var(--dn)}
#arena .s-flat,#arena .s-waiting,#arena .s-done{background:rgba(133,146,176,.15);color:var(--mu)} #arena .s-ko{background:#2a1520;color:var(--dn)}
#arena .bar{height:6px;border-radius:6px;background:#0c1222;margin-top:8px;overflow:hidden}
#arena .bar i{display:block;height:100%;border-radius:6px}
#arena .bub{position:relative;margin-top:10px;background:#0d1426;border:1px solid var(--ln);border-radius:12px;padding:8px 10px;font-size:12px;color:#cfd7ea;min-height:52px}
#arena .bub:before{content:"";position:absolute;top:-6px;left:18px;width:10px;height:10px;background:#0d1426;border-left:1px solid var(--ln);border-top:1px solid var(--ln);transform:rotate(45deg)}
#arena .tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}
#arena .tg{font-size:9.5px;font-weight:800;letter-spacing:.06em;padding:2px 6px;border-radius:6px;border:1px solid var(--ln);color:var(--mu)}
#arena .tg.q{color:var(--gd);border-color:rgba(255,204,51,.5)} #arena .tg.d{color:var(--dn);border-color:rgba(255,77,94,.6)}
#arena .tg.s{color:var(--up);border-color:rgba(47,224,122,.5)} #arena .tg.n{color:var(--cy);border-color:rgba(62,240,255,.5)}
#arena .feed{max-height:900px;overflow:auto}
#arena .ev{display:grid;grid-template-columns:62px 1fr;gap:8px;padding:9px 4px;border-bottom:1px solid var(--ln);font-size:12px}
#arena .ev .t{color:var(--mu);font-variant-numeric:tabular-nums;font-size:11px}
#arena .ev b{font-weight:800}
#arena .k-long b{color:var(--up)} #arena .k-short b{color:var(--dn)} #arena .k-win .x{color:var(--up)} #arena .k-loss .x{color:var(--dn)}
#arena .k-ko{background:rgba(255,77,94,.07)} #arena .k-join{background:rgba(62,240,255,.06)} #arena .k-trophy{background:rgba(255,204,51,.08)}
#arena table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:12.5px}
#arena th{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.06em;text-align:right;padding:7px;border-bottom:1px solid var(--ln);white-space:nowrap}
#arena td{padding:7px;border-bottom:1px solid var(--ln);text-align:right;white-space:nowrap}
#arena th:nth-child(2),#arena td:nth-child(2){text-align:left}
#arena .tw{overflow-x:auto}
#arena .modal{position:fixed;inset:0;background:rgba(5,8,15,.78);display:none;align-items:flex-start;justify-content:center;padding:30px 14px;z-index:50;overflow:auto}
#arena .modal.on{display:flex}
#arena .mc{width:min(860px,100%);background:var(--p1);border:1px solid var(--ln);border-radius:16px;padding:18px}
#arena .x-btn{float:right;cursor:pointer;color:var(--mu);font-size:12px;border:1px solid var(--ln);border-radius:8px;padding:4px 8px}
#arena .kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin:12px 0}
#arena .kv div{background:var(--p2);border:1px solid var(--ln);border-radius:10px;padding:8px}
#arena .kv div>span{display:block;font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.06em}
#arena .kv b{font-size:15px}
#arena .tl{font-size:12px;border-bottom:1px solid var(--ln);padding:8px 0}
#arena .ctl{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
#arena .ctl button{cursor:pointer;font:600 12px Inter,sans-serif;color:var(--mu);background:var(--p1);border:1px solid var(--ln);border-radius:8px;padding:6px 10px}
#arena .ctl button.on{color:var(--fg);border-color:var(--cy)}
#arena .rules li{margin:6px 0}
#arena .empty{color:var(--mu);padding:20px;text-align:center}

#arena .switch{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 4px}
@media(max-width:900px){#arena .switch{grid-template-columns:repeat(2,1fr)}}
#arena .sw{cursor:pointer;border:1px solid var(--ln);background:var(--p1);border-radius:14px;padding:10px 12px;transition:border-color .12s}
#arena .sw:hover{border-color:var(--cy)}
#arena .sw.on{border-color:var(--cy);box-shadow:0 0 0 1px var(--cy) inset;background:linear-gradient(180deg,#14223f,var(--p1))}
#arena .sw .t1{font-weight:800;font-size:14px}
#arena .sw .t2{font-size:11px;color:var(--mu);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#arena .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;background:var(--mu)}
#arena .dot.on{background:var(--up);box-shadow:0 0 8px var(--up)}
#arena .chips{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}
#arena .chip{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:7px;background:#0d1426;border:1px solid var(--ln)}
#arena .tickrow{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end;font-size:12px;font-variant-numeric:tabular-nums}
#arena .tickrow span b{color:var(--fg)}
#arena .s-multi{background:rgba(62,240,255,.12);color:var(--cy)}
#arena .abtn{cursor:pointer;font:700 11px Inter,sans-serif;color:var(--mu);background:var(--p2);border:1px solid var(--ln);border-radius:8px;padding:5px 9px;margin:0 6px 6px 0}
#arena .abtn.on{color:var(--bg);background:var(--cy);border-color:var(--cy)}
#arena .hl{display:grid;grid-template-columns:70px 58px 1fr 56px;gap:8px;padding:8px 4px;border-bottom:1px solid var(--ln);font-size:12px}
#arena .two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){#arena .two{grid-template-columns:1fr}}
#arena .btn{cursor:pointer;font:700 12px Inter,sans-serif;color:var(--fg);background:var(--p2);border:1px solid var(--ln);border-radius:10px;padding:8px 12px}
#arena .btn:hover{border-color:var(--cy)}
#arena .city{position:relative;border-radius:14px;overflow:hidden;padding:18px 14px 14px;background:linear-gradient(180deg,#070a1c 0%,#151b4a 55%,#2a1f4f 75%,#0b0e1a 100%)}
#arena .sky{position:absolute;inset:0;pointer-events:none}
#arena .star{position:absolute;width:2px;height:2px;background:#fff;opacity:.7;animation:tw 3s infinite}
@keyframes tw{50%{opacity:.15}}
#arena .moon{position:absolute;right:7%;top:5%;width:46px;height:46px;border-radius:50%;background:#fff6d5;box-shadow:0 0 40px 8px rgba(255,246,213,.25)}
#arena .far{position:absolute;left:0;right:0;bottom:120px;height:120px;opacity:.35;background:
 linear-gradient(#1b2150,#1b2150) 2% 100%/6% 60% no-repeat,linear-gradient(#1b2150,#1b2150) 10% 100%/4% 85% no-repeat,
 linear-gradient(#1b2150,#1b2150) 18% 100%/7% 45% no-repeat,linear-gradient(#1b2150,#1b2150) 30% 100%/5% 75% no-repeat,
 linear-gradient(#1b2150,#1b2150) 45% 100%/6% 55% no-repeat,linear-gradient(#1b2150,#1b2150) 60% 100%/5% 90% no-repeat,
 linear-gradient(#1b2150,#1b2150) 72% 100%/7% 50% no-repeat,linear-gradient(#1b2150,#1b2150) 85% 100%/5% 80% no-repeat,
 linear-gradient(#1b2150,#1b2150) 95% 100%/6% 60% no-repeat}
#arena .city-title{position:relative;text-align:center;font-size:20px;color:#fff;text-shadow:0 0 12px var(--cy),0 0 2px #fff}
#arena .city-sub{position:relative;text-align:center;color:#b8c2e0;font-size:12px;margin:8px 0 14px}
#arena .city-sub .win{display:inline-block;vertical-align:middle;margin:0 2px}
#arena .towers{position:relative;display:flex;justify-content:center;align-items:flex-end;gap:22px;flex-wrap:wrap;min-height:330px}
#arena .tw-wrap{cursor:pointer;display:flex;flex-direction:column;align-items:center;transition:transform .15s}
#arena .tw-wrap:hover{transform:translateY(-6px)}
#arena .tw-wrap:hover .tower{box-shadow:0 0 0 2px var(--c),0 0 40px -4px var(--c)}
#arena .neon{font-family:'Press Start 2P',monospace;font-size:9px;color:var(--c);text-shadow:0 0 8px var(--c);padding:6px 8px;border:2px solid var(--c);border-radius:6px;background:#0a0e19;margin-bottom:32px;white-space:nowrap;animation:neon 2.6s infinite}
@keyframes neon{0%,100%{opacity:1}92%{opacity:1}94%{opacity:.4}96%{opacity:1}}
#arena .tower{position:relative;width:150px;background:linear-gradient(90deg,var(--g),#0c1022 60%,var(--g));border:2px solid var(--c);border-bottom:none;border-radius:6px 6px 0 0;padding:44px 12px 52px;transition:box-shadow .15s}
#arena .antenna{position:absolute;top:-26px;left:50%;width:3px;height:24px;background:#8592b0;transform:translateX(-50%)}
#arena .antenna::after{content:"";position:absolute;top:-5px;left:-3px;width:9px;height:9px;border-radius:50%;background:#555}
#arena .antenna.on::after{background:#ff4d5e;box-shadow:0 0 10px #ff4d5e;animation:blink 1.2s infinite}
#arena .bill{position:absolute;top:6px;left:6px;right:6px;font-size:9.5px;line-height:1.25;text-align:center;color:#fff;background:#05070f;border:1px solid var(--c);border-radius:4px;padding:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#arena .wins{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}
#arena .win{display:block;width:22px;height:15px;border-radius:2px;background:#1a2036;box-shadow:inset 0 0 0 1px rgba(255,255,255,.05)}
#arena .w-on{background:#c8d3ff;opacity:.55}
#arena .w-dim{background:#262c45}
#arena .w-dimg{background:#20402f}
#arena .w-green{background:#2fe07a;box-shadow:0 0 8px rgba(47,224,122,.6)}
#arena .w-pink{background:#c0566b}
#arena .w-gold{background:#ffd23e;box-shadow:0 0 10px rgba(255,210,62,.8);animation:flick 2s infinite}
#arena .w-red{background:#ff2a44;box-shadow:0 0 12px #ff2a44;animation:blink .8s infinite}
#arena .w-cyan{background:#3ef0ff;box-shadow:0 0 8px #3ef0ff}
@keyframes flick{40%{opacity:.75}45%{opacity:1}70%{opacity:.85}}
#arena .door{position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:44px;height:40px;background:#05070f;border:2px solid var(--c);border-bottom:none;border-radius:20px 20px 0 0;display:grid;place-items:center}
#arena .door span{font-size:8px;font-weight:800;color:var(--c);letter-spacing:.05em}
#arena .tw-info{text-align:center;font-size:12px;margin-top:8px;color:#e9eefb;max-width:170px}
#arena .street{position:relative;margin-top:0;height:44px;background:#151926;border-top:3px solid #2a3150;overflow:hidden}
#arena .street::after{content:"";position:absolute;left:0;right:0;top:50%;border-top:2px dashed #ffcc3355}
#arena .tape{position:absolute;inset:6px 0;display:flex;align-items:center;overflow:hidden;z-index:1}
#arena .tape-in{white-space:nowrap;font-size:12px;color:#ffe9a8;animation:scroll 120s linear infinite;padding-left:100%}
#arena .tape-in span{margin-right:14px}
#arena .tape-in .sep{color:#ff3ea5}
@keyframes scroll{to{transform:translateX(-100%)}}
#arena .yard{position:relative;margin-top:12px;background:linear-gradient(180deg,#14261a,#0c1610);border:1px solid #234b30;border-radius:12px;padding:10px}
#arena .yard-t{font-size:9px;color:#9fb8a6;margin-bottom:8px}
#arena .stones{display:flex;flex-wrap:wrap;gap:8px}
#arena .stone{cursor:pointer;width:46px;height:52px;background:linear-gradient(#8b93a7,#5d6478);border-radius:20px 20px 4px 4px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#1d2230;font-weight:800;font-size:9px;box-shadow:0 3px 0 #2f3446}
#arena .stone small{font-size:7.5px;font-weight:700;max-width:42px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* inside a tower */
#arena .tower-in{border-radius:14px;padding:12px;background:linear-gradient(180deg,#0b0f1e,#0a0e19)}
#arena .tin-top{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin-bottom:12px}
#arena .tin-name{font-size:14px;color:var(--c);text-shadow:0 0 10px var(--c)}
#arena .tin-grid{display:grid;grid-template-columns:1fr 320px;gap:14px}
@media(max-width:1000px){#arena .tin-grid{grid-template-columns:1fr}}
#arena .building{border:3px solid var(--c);border-radius:10px 10px 0 0;background:#0c1124;box-shadow:0 0 30px -10px var(--c)}
#arena .penthouse{background:linear-gradient(180deg,#2a2208,#141024);border-bottom:3px solid var(--c);padding:8px 10px 10px;border-radius:7px 7px 0 0}
#arena .ph-t{font-size:9px;color:#ffcc33;margin-bottom:6px}
#arena .floor{display:flex;border-bottom:3px solid #222a48;background:repeating-linear-gradient(90deg,#10162c 0 60px,#121a33 60px 120px)}
#arena .fnum{width:34px;flex:0 0 34px;display:grid;place-items:center;font-size:9px;color:#6d7aa0;border-right:2px solid #222a48;background:#0b1022}
#arena .desks{display:grid;grid-template-columns:repeat(4,1fr);flex:1;min-height:118px}
@media(max-width:700px){#arena .desks{grid-template-columns:repeat(2,1fr)}}
#arena .desk{position:relative;cursor:pointer;padding:6px 4px 4px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;border-right:1px dashed #1d2542}
#arena .desk:hover{background:rgba(62,240,255,.06)}
#arena .station{position:relative;width:96px;height:66px}
#arena .table{position:absolute;bottom:0;left:6px;right:6px;height:14px;background:#6b4a2e;border-radius:3px;box-shadow:0 3px 0 #3e2a1a}
#arena .monitor{position:absolute;bottom:14px;right:8px;width:34px;height:24px;background:#05070f;border:3px solid #2a3150;border-radius:3px;display:grid;place-items:center;font-size:12px}
#arena .monitor::after{content:"";position:absolute;bottom:-7px;left:50%;width:6px;height:5px;background:#2a3150;transform:translateX(-50%)}
#arena .pulse{display:block;width:20px;height:2px;background:#3ea8ff;box-shadow:0 0 6px #3ea8ff;animation:flick 1.5s infinite}
#arena .guy{position:absolute;bottom:12px;left:14px;width:28px;height:42px}
#arena .guy i{position:absolute;display:block}
#arena .guy .head{left:7px;top:4px;width:14px;height:14px;border-radius:4px;background:var(--skin)}
#arena .guy .hair{left:6px;top:1px;width:16px;height:7px;border-radius:4px 4px 1px 1px;background:var(--hair);z-index:1}
#arena .guy .body{left:3px;top:18px;width:22px;height:18px;border-radius:6px 6px 2px 2px;background:var(--c)}
#arena .guy .arm{top:22px;width:6px;height:12px;border-radius:3px;background:var(--c);filter:brightness(.8)}
#arena .guy .arm.l{left:0}#arena .guy .arm.r{right:0}
#arena .guy.idle .arm,#arena .guy.trading .arm{animation:type .35s infinite alternate}
#arena .guy.idle .arm.r,#arena .guy.trading .arm.r{animation-delay:.17s}
@keyframes type{to{transform:translateY(-3px)}}
#arena .guy.trading .head{animation:lean 2s infinite}
@keyframes lean{50%{transform:translateX(2px)}}
#arena .guy.danger{animation:shake .25s infinite}
@keyframes shake{25%{transform:translateX(-1px)}75%{transform:translateX(1px)}}
#arena .guy.sleep .head,#arena .guy.sleep .hair{transform:translateY(9px) rotate(-12deg)}
#arena .guy.sleep .arm{top:26px;transform:rotate(70deg)}
#arena .guy.entering{animation:walk 1s infinite}
@keyframes walk{50%{transform:translateY(-2px)}}
#arena .crown{position:absolute;left:19px;top:-14px;font-size:16px;z-index:3;animation:walk 1.6s infinite}
#arena .fx{position:absolute;left:44px;top:-6px;font-size:13px;z-index:3}
#arena .fx.sweat{left:6px;top:4px;animation:drip 1s infinite}
@keyframes drip{to{transform:translateY(8px);opacity:0}}
#arena .fx.zz{left:40px;top:-2px;color:#9fb0ff;font-weight:800;font-size:12px;animation:zz 2.4s infinite}
#arena .fx.zz small{font-size:9px}
@keyframes zz{0%{opacity:0;transform:translate(0,4px)}50%{opacity:1}100%{opacity:0;transform:translate(8px,-10px)}}
#arena .fx.cash{left:62px;top:-12px;animation:walk 1.2s infinite}
#arena .lamp{position:absolute;top:4px;right:6px;width:10px;height:10px;border-radius:50%;background:#ff2a44;box-shadow:0 0 14px 3px #ff2a44;animation:blink .7s infinite}
#arena .plate{text-align:center;font-size:10.5px;line-height:1.25;margin-top:4px;max-width:120px}
#arena .plate .pn{display:block;color:#cfd7ea;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:118px}
#arena .bubble{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);width:220px;background:#f4f6ff;color:#121828;font-size:11.5px;line-height:1.35;padding:8px 10px;border-radius:10px;z-index:20;box-shadow:0 8px 24px rgba(0,0,0,.5)}
#arena .bubble::after{content:"";position:absolute;top:100%;left:50%;border:7px solid transparent;border-top-color:#f4f6ff;transform:translateX(-50%)}
#arena .desk:hover .bubble{display:block}
#arena .s-danger{background:rgba(255,42,68,.08)}
#arena .penthouse .desk{max-width:240px;margin:0 auto}
#arena .lobby{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;padding:12px;background:repeating-linear-gradient(45deg,#1a1f33 0 12px,#161b2e 12px 24px);border-bottom:3px solid var(--c)}
#arena .statue{display:flex;gap:10px;align-items:center;font-size:12.5px}
#arena .ped{font-size:28px;background:#2a3150;border-radius:8px;padding:2px 8px}
#arena .basement{background:#080b16;padding:10px}
#arena .bench{display:flex;flex-wrap:wrap;gap:12px}
#arena .waiter{position:relative;width:96px;height:96px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;font-size:10px;text-align:center;cursor:pointer}
#arena .waiter .guy{position:relative;left:auto;bottom:auto;margin-bottom:4px}
#arena .waiter small{color:#cfd7ea;line-height:1.2;max-width:96px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#arena .waiter em{color:var(--mu);font-size:9.5px}
#arena .waiter.q{opacity:.65}
#arena .side .stones .stone{width:42px;height:48px}
@media(max-width:760px){#arena .top>div:last-child{max-width:100%!important;flex-wrap:wrap}#arena .towers{gap:14px}#arena .tower{width:132px}#arena .win{width:18px}}
#arena .finalbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:center;margin:0 0 12px;padding:10px;border-radius:12px;background:linear-gradient(90deg,#2a1d05,#3a2a08,#2a1d05);border:1px solid #ffcc3366;color:#ffe9a8}
#arena .finalbar .px{font-size:10px;color:#ffcc33}
#arena .finalbar b{font-family:'Press Start 2P',monospace;font-size:13px;color:#fff;letter-spacing:.04em}
#arena .finals{position:relative;margin-top:12px;background:#120f22;border:1px solid #ffcc3355;border-radius:12px;padding:12px}
#arena .fin-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:900px){#arena .fin-grid{grid-template-columns:1fr 1fr}}
@media(max-width:560px){#arena .fin-grid{grid-template-columns:1fr}}
#arena .fin{background:#0c1124;border:1px solid var(--ln);border-radius:10px;padding:10px;font-size:12px;color:#dfe5f5}
#arena .fin-h{margin-bottom:6px}
#arena .cks{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
#arena .ck{font-size:10px;padding:2px 6px;border-radius:6px;border:1px solid var(--ln)}
#arena .ck.ok{color:#2fe07a;border-color:#2fe07a55}#arena .ck.no{color:#ff6b7d;border-color:#ff4d5e55}
#arena .census{text-align:center;font-size:12px;color:#b8c2e0;margin:-4px 0 12px}
#arena .building2{border:3px solid var(--c);border-radius:10px 10px 0 0;background:#0c1124;box-shadow:0 0 30px -10px var(--c);overflow:hidden}
#arena .roof2{text-align:center;padding:8px;background:linear-gradient(180deg,var(--g),#0c1124);border-bottom:3px solid var(--c)}
#arena .roof2 .px{font-size:10px;color:var(--c);text-shadow:0 0 8px var(--c)}
#arena .apt{display:flex;border-bottom:4px solid #2a3150}
#arena .apt.pent{background:linear-gradient(180deg,#2a2208,#16122a)}
#arena .fnum2{flex:0 0 30px;display:grid;place-items:center;font-size:9px;color:#8592b0;background:#090d1c;border-right:2px solid #2a3150}
#arena .rooms2{position:relative;flex:1;height:132px;display:grid;grid-template-columns:40% 30% 30%;overflow:hidden}
#arena .room{position:relative;border-right:3px solid #2a3150}
#arena .room:last-of-type{border-right:none}
#arena .rl{position:absolute;top:4px;left:6px;font-size:9px;font-weight:800;letter-spacing:.06em;color:#8592b0;z-index:1}
#arena .day .r-office{background:linear-gradient(180deg,#1b2747 0 72%,#3a2f2a 72%)}
#arena .day .r-lounge{background:linear-gradient(180deg,#2a2346 0 72%,#40302a 72%)}
#arena .day .r-bed{background:linear-gradient(180deg,#232a40 0 72%,#33303c 72%)}
#arena .night .room{background:linear-gradient(180deg,#0d1226 0 72%,#1d1a22 72%)}
#arena .night .r-bed{background:linear-gradient(180deg,#121633 0 72%,#1f1c28 72%)}
#arena .pent .room{background:linear-gradient(180deg,#2b2410 0 72%,#3a2c18 72%)!important}
#arena .wnd{position:absolute;top:18px;right:10%;width:34px;height:30px;border:3px solid #3a4468;border-radius:3px;background:linear-gradient(#7fb7ff,#bfe0ff)}
#arena .wnd.w2{right:auto;left:42%}
#arena .night .wnd{background:linear-gradient(#081030,#1a2350);box-shadow:inset 6px -6px 0 -3px #fff6d5}
#arena .alarm{animation:alarmbg 1.2s infinite}
@keyframes alarmbg{50%{box-shadow:inset 0 0 40px rgba(255,42,68,.35)}}
#arena .siren{position:absolute;top:4px;right:8px;width:12px;height:8px;border-radius:6px 6px 0 0;background:#ff2a44;box-shadow:0 0 16px 4px #ff2a44;animation:blink .6s infinite}
#arena .sofa{position:absolute;bottom:26%;left:14%;width:46%;height:22px;background:#7a3e6a;border-radius:8px 8px 3px 3px;box-shadow:0 -8px 0 -2px #8f4a7d}
#arena .tv{position:absolute;top:18px;left:22%;width:40px;height:24px;background:#05070f;border:3px solid #2a3150;border-radius:3px;box-shadow:inset 0 0 10px #3ea8ff}
#arena .night .tv{box-shadow:none}
#arena .coffee{position:absolute;bottom:28%;right:10%;width:14px;height:24px;background:#556;border-radius:3px;box-shadow:0 -6px 0 -3px #c33}
#arena .plant{position:absolute;bottom:28%;right:26%;width:12px;height:12px;background:#a0522d;border-radius:2px;box-shadow:0 -12px 0 2px #2fa35a}
#arena .furn{position:absolute;inset:0;pointer-events:none}
#arena .dk{position:absolute;bottom:22px;width:7.2%;height:12px;background:#6b4a2e;border-radius:2px;box-shadow:0 3px 0 #3e2a1a;z-index:2}
#arena .dk .scr{position:absolute;bottom:12px;left:62%;width:24px;height:18px;background:#05070f;border:2px solid #3a4468;border-radius:2px}
#arena .day .dk .scr{box-shadow:inset 0 0 8px #3ea8ff}
#arena .bd2{position:absolute;bottom:18px;width:6%;height:16px;background:#e8e8f2;border-radius:3px;box-shadow:0 4px 0 #6b4a2e;z-index:1}
#arena .bd2 .pil{position:absolute;left:2px;top:-5px;width:12px;height:7px;background:#fff;border-radius:3px}
#arena .bd2 .blk{position:absolute;right:0;top:0;width:65%;height:100%;background:#3e6fd8;border-radius:0 3px 3px 0}
#arena .pent .bd2 .blk{background:#c9a227}
#arena .sp{position:absolute;bottom:24px;width:28px;margin-left:-14px;z-index:3;cursor:pointer;transition:left var(--dur,2.4s) linear}
#arena .sp .guy{position:relative;left:0;bottom:0;width:28px;height:36px}
#arena .sp .legs{position:absolute;left:8px;top:34px;width:12px;height:10px}
#arena .sp .legs i{position:absolute;top:0;width:5px;height:9px;background:#2b3350;border-radius:2px}
#arena .sp .legs i:first-child{left:0}#arena .sp .legs i:last-child{right:0}
#arena .sp.walking .legs i:first-child{animation:legA .35s infinite alternate}
#arena .sp.walking .legs i:last-child{animation:legB .35s infinite alternate}
@keyframes legA{from{transform:rotate(25deg)}to{transform:rotate(-25deg)}}
@keyframes legB{from{transform:rotate(-25deg)}to{transform:rotate(25deg)}}
#arena .sp.walking .guy{animation:bob .35s infinite alternate}
@keyframes bob{to{transform:translateY(-2px)}}
#arena .sp.flip .guy,#arena .sp.flip .legs{transform:scaleX(-1)}
#arena .sp.sit{bottom:30px;z-index:1}
#arena .sp.sit .legs{display:none}
#arena .sp.sit .guy .arm{animation:type .3s infinite alternate}
#arena .sp.sit .guy .arm.r{animation-delay:.15s}
#arena .sp.sleep{bottom:30px;z-index:2}
#arena .sp.sleep .guy{transform:rotate(-90deg) translate(-6px,-4px)}
#arena .sp.sleep .legs{display:none}
#arena .sp.panic .guy{animation:shake .2s infinite}
#arena .sp.stand{display:inline-block;margin:0 6px;bottom:auto}
#arena .tag2{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);margin-bottom:2px;font-size:8.5px;font-weight:700;white-space:nowrap;color:#cfd7ea;background:#05070fcc;padding:1px 4px;border-radius:4px}
#arena .sp.sit .tag2,#arena .sp.sleep .tag2{margin-bottom:14px}
#arena .sp.alt .tag2{margin-bottom:16px}#arena .sp.alt.sit .tag2,#arena .sp.alt.sleep .tag2{margin-bottom:28px}#arena .sp.alt .chip2{margin-bottom:30px}#arena .sp.alt.sit .chip2{margin-bottom:42px}
#arena .chip2{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);margin-bottom:16px;font-size:9px;font-weight:800;white-space:nowrap;background:#0b1022;border:1px solid #2a3150;padding:1px 5px;border-radius:6px}
#arena .sp.sit .chip2{margin-bottom:28px}
#arena .crown2{position:absolute;top:-14px;left:7px;font-size:14px;z-index:4}
#arena .sweat2{position:absolute;top:0;left:-6px;font-size:11px;animation:drip 1s infinite}
#arena .zz2{position:absolute;top:-22px;left:18px;color:#9fb0ff;font-weight:800;font-size:11px;animation:zz 2.4s infinite}
#arena .cash2{position:absolute;top:-10px;left:24px;font-size:12px;animation:walk 1.2s infinite}
#arena .new2{position:absolute;top:-6px;left:-6px;font-size:11px}
#arena .bub2{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);margin-bottom:36px;width:230px;background:#f4f6ff;color:#121828;font-size:11.5px;line-height:1.35;padding:8px 10px;border-radius:10px;z-index:30;box-shadow:0 8px 24px rgba(0,0,0,.5)}
#arena .sp:hover .bub2{display:block}
#arena .sp:hover{z-index:20}
#arena .lobby2{display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between;padding:12px;background:repeating-linear-gradient(45deg,#1a1f33 0 12px,#161b2e 12px 24px);border-top:4px solid #2a3150;border-bottom:3px solid var(--c)}
#arena .cage{display:flex;gap:10px;align-items:center;font-size:12.5px;background:repeating-linear-gradient(90deg,#3a4468 0 2px,transparent 2px 10px);padding:6px 10px;border-radius:8px}
#arena .elev{background:#0b0f1e;border:2px solid #3a4468;border-radius:8px;padding:6px 10px;min-width:180px}
#arena .arr{display:flex;flex-wrap:wrap;align-items:flex-end;min-height:56px;padding-top:16px}
#arena .empty2{min-height:60px}
@media(max-width:700px){#arena .rooms2{height:118px}#arena .sp{transform:scale(.8);transform-origin:bottom center}#arena .rl{font-size:7.5px}#arena .wnd,#arena .tv{display:none}}
@media(max-width:700px){#arena{padding:10px}#arena .tag2{display:none}#arena .sp:hover .tag2{display:block}
#arena .chip2{font-size:7.5px;padding:0 3px;margin-bottom:12px}#arena .sp.sit .chip2{margin-bottom:22px}#arena .sp.alt .chip2{margin-bottom:22px}#arena .sp.alt.sit .chip2{margin-bottom:32px}
#arena .census{font-size:11px}#arena .tin-name{font-size:11px}#arena .finalbar b{font-size:11px}#arena .finalbar{padding:8px}
#arena .city-title{font-size:15px}#arena .moon{display:none}#arena .city-sub{font-size:11px}#arena .neon{font-size:7.5px;margin-bottom:26px}
#arena .towers{gap:10px 12px}#arena .tw-wrap{width:46%;align-items:center}#arena .tower{width:100%;max-width:150px;padding:40px 8px 50px}
#arena .wins{gap:5px}#arena .wins .win{width:100%;height:13px}#arena .city-sub .win{width:14px;height:10px}#arena .tw-info{font-size:11px}
#arena .fnum2{flex-basis:20px;font-size:8px}#arena .rl{font-size:7px;left:3px}#arena .sofa,#arena .coffee,#arena .plant{transform:scale(.7);transform-origin:bottom}
#arena .lobby2{gap:8px}#arena .statue,#arena .cage{font-size:11.5px}#arena .bub2{width:180px}
#arena .tin-top .btn{padding:6px 9px;font-size:11px}
#arena .dk .scr{width:14px;height:11px;left:58%}#arena .sp.d0 .chip2,#arena .sp.d0 .tag2{left:-4px;transform:none}}
#arena .stale{margin-bottom:10px;padding:10px 12px;border-radius:10px;background:#3a2408;border:1px solid #ffb02088;color:#ffd58a;font-size:12.5px}
#arena .pt{font-size:9.5px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#aeb8d2}
#arena .pt b{color:#e9eefb}#arena .pt.f{color:#7fd8ff}#arena .pt.e{color:#c9b8ff}#arena .pt-r{color:#ff9e5e}
#arena .card .pt{font-size:11px;margin-top:8px;white-space:normal}
#arena .propdesk{display:flex;gap:10px;align-items:center;font-size:12px;background:#0d1a2e;border:1px solid #3ea8ff55;border-radius:10px;padding:8px 10px}
#arena .propdesk .ped{font-size:22px}
#arena .fund2{position:absolute;bottom:100%;right:-10px;font-size:11px;margin-bottom:-2px}
#arena .pt.d{color:#ff6b7d}
#arena .hof{border-color:#3ea8ff55}#arena .hof-r{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px;font-size:12px;padding:5px 0;border-bottom:1px solid var(--ln)}
#arena .aptR{flex:1;min-width:0;display:flex;flex-direction:column}#arena .aptR>.rooms2{flex:0 0 auto}
#arena .ledger{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#2a3150;border-top:2px solid #2a3150}
#arena .pent .ledger{grid-template-columns:1fr}
#arena .lg{background:#090d1c;padding:4px 6px;font-size:10.5px;line-height:1.3;cursor:pointer;min-width:0}
#arena .lg:hover{background:#121a33}
#arena .lg-n{display:block;color:#cfd7ea;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#arena .lg-v{white-space:nowrap}#arena .lg-v em{font-style:normal;color:#6f7b98;font-size:9.5px}
#arena .tsq{position:relative;margin:4px auto 16px;max-width:760px;padding:14px 14px 10px;border-radius:10px;background:#07060d;border:6px solid #1c1830;
  box-shadow:0 0 0 2px #3a2f5c,0 0 40px -6px #ff3ea5,0 0 60px -12px #3ef0ff;overflow:hidden}
#arena .tsq .bulbs{position:absolute;inset:2px;border:3px dotted #ffd84a;border-radius:6px;opacity:.55;pointer-events:none;animation:blink 1.4s steps(2) infinite}
#arena .bb-h{text-align:center;font-size:9px;color:#ff7ac8;text-shadow:0 0 8px #ff3ea5;margin-bottom:10px;letter-spacing:.06em}
#arena .bb-screens{display:grid;grid-template-columns:1fr 1fr;gap:12px}
#arena .bb-s{text-align:center;padding:12px 8px;border-radius:6px;background:#020305;border:2px solid #1d2238;
  background-image:radial-gradient(rgba(255,255,255,.05) 1px,transparent 1.2px);background-size:4px 4px}
#arena .bb-l{font-size:9px;color:#8fa0c8;margin-bottom:8px}
#arena .led{display:block;font-family:'Press Start 2P',monospace;font-size:clamp(18px,4.6vw,34px);color:#e8ecff;letter-spacing:.02em;font-variant-numeric:tabular-nums;text-shadow:0 0 10px currentColor}
#arena .led.g{color:#2fff8a}#arena .led.r{color:#ff4d6a}
#arena .bb-per{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 14px;margin:10px 0 6px;font-size:11.5px;color:#cfd7ea}
#arena .bb-t i{font-style:normal;font-weight:800}#arena .bb-t em{font-style:normal;color:#8592b0}
#arena .bb-crawl{overflow:hidden;white-space:nowrap;border-top:1px solid #241f3a;border-bottom:1px solid #241f3a;padding:5px 0;font-family:'Press Start 2P',monospace;font-size:9px;color:#ffd84a}
#arena .bb-in{display:inline-block;animation:crawl 40s linear infinite}
#arena .bb-in span{padding:0 6px}#arena .bb-in .sep{color:#ff3ea5}
@keyframes crawl{from{transform:translateX(0)}to{transform:translateX(-50%)}}
#arena .bb-note{font-size:10px;color:#6f7b98;text-align:center;margin-top:6px}
#arena .pod{background:#0f1530;border:1px solid var(--ln);border-radius:8px;padding:6px 8px;margin-top:5px}
#arena .pod.p1{border-color:#ffcc3388;background:linear-gradient(90deg,#2a2208,#0f1530)}
#arena .pod-l{display:flex;gap:6px;align-items:center;min-width:0}#arena .pod-l b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#arena .medal{font-size:16px}#arena .lnk{cursor:pointer;text-decoration:underline}
#arena .pod-r{margin:2px 0 0 28px;font-size:11.5px}#arena .okn{font-size:10.5px;color:#8592b0}#arena .okn.all{color:#2fe07a}
@media(max-width:700px){#arena .ledger{grid-template-columns:1fr 1fr}#arena .tsq{padding:12px 8px 8px;border-width:4px}#arena .bb-screens{gap:8px}#arena .bb-h{font-size:7.5px}#arena .bb-l{font-size:7.5px}#arena .bb-per{font-size:10.5px}}
#arena .rulebook{background:#0d1426;border:1px solid var(--ln);border-radius:10px;padding:10px 12px;margin:8px 0 14px;font-size:12.5px}
#arena .rulebook li{margin:4px 0}
</style>
"""

JS = r"""
<script>
(function(){
const D = __DATA__;
const R = document.getElementById('arena');
const COL = {Striker:'#ff8a4c',Counter:'#b07cff',Rider:'#3ea8ff',Sprinter:'#ffd23e',Brain:'#2fe0c0',Hypebeast:'#ff3ea5',Boss:'#8592b0'};
const esc = s => String(s==null?'':s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const money = (x, sign=true) => x==null ? '–' : (sign && x>0?'+':x<0?'−':'') + '$' + Math.abs(Math.round(x)).toLocaleString('en-GB');
const num = x => x==null ? '–' : Number(x).toLocaleString('en-GB',{maximumFractionDigits:2});
const cls = x => x>0?'up':x<0?'dn':'mu';
const ini = n => n.replace(/[^A-Za-z0-9 ]/g,' ').split(/\s+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('').toUpperCase();
const short = a => String(a).replace('-USD','');
let st = {arena:D.order[0], view:'city', tab:'arena', sort:'pnl', filter:'all', asset:null};
try { st = Object.assign(st, JSON.parse(localStorage.getItem('arena_ui2')||'{}')); } catch(e) {}
if(!D.arenas[st.arena]) st.arena = D.order[0];
const save = () => { try { localStorage.setItem('arena_ui2', JSON.stringify({arena:st.arena, view:st.view, tab:st.tab, sort:st.sort, filter:st.filter})); } catch(e) {} };
let A, M, maxAbs;
function pick(){ A = D.arenas[st.arena]; M = A.meta;
  maxAbs = Math.max(1, ...A.fighters.filter(f=>f.status==='active').map(f=>Math.abs(f.pnl||0))); }

function spark(a, w=110, h=28){
  if(!a || a.length<2) return '';
  const mn=Math.min(...a,0), mx=Math.max(...a,0), r=(mx-mn)||1;
  const pts=a.map((v,i)=>`${(i/(a.length-1)*w).toFixed(1)},${(h-(v-mn)/r*h).toFixed(1)}`).join(' ');
  const z=(h-(0-mn)/r*h).toFixed(1); const c=a[a.length-1]>=0?'#2fe07a':'#ff4d5e';
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><line x1="0" x2="${w}" y1="${z}" y2="${z}" stroke="#243050"/><polyline fill="none" stroke="${c}" stroke-width="1.8" points="${pts}"/></svg>`;
}
function stance(f){
  const m={long:'▲ LONG',short:'▼ SHORT',flat:'WAITING',waiting:'ENTERING',ko:'K.O.',multi:(f.opens||[]).length+' OPEN'};
  return `<span class="stance s-${f.pos}">${m[f.pos]||f.pos}</span>`;
}
function propTag(f, full){
  const p=f.prop; if(!p) return '';
  const R=(D.arenas.nq&&D.arenas.nq.prop||{}).rules||{payday:150};
  const k = full?` · <span class="mu">${p.lots_now} lot${p.lots_now>1?'s':''} next trade</span>`:'';
  const room = full?` · room <b>$${p.room.toLocaleString('en-GB')}</b>`:'';
  if(p.dead) return `<div class="pt d">💀 BLOWN at the close · out</div>`;
  const halt = p.halted?` <span class="pt-r">⏸ done for today</span>`:'';
  if(p.phase==='funded'){
    const goal = p.funded_days?` · <span class="${p.paydays===p.funded_days?'up':'mu'}">${p.paydays}/${p.funded_days} days ≥$${R.payday}</span>`:' · first funded day';
    const wi = full&&p.whatif_days?`<div class="mu" style="font-size:10.5px">If it stopped at +$${R.payday}: ${p.whatif_paydays}/${p.whatif_days} days ≥$${R.payday}</div>`:'';
    return `<div class="pt f">💼 FUNDED <b>${money(p.balance,false)}</b>${goal}${room}${k}${halt}</div>${wi}`;
  }
  const dots = `<span class="${p.good_days?'up':''}">${p.good_days}/${p.need_days} days</span>`;
  return `<div class="pt e">📝 EVAL ${dots} · <b>${money(p.balance,false)}</b>${room}${k}${halt}</div>`;
}
function propDesk(a){
  const P=a.prop; if(!P) return '';
  const r=P.rules, B=P.boss;
  return `<div class="propdesk"><div class="ped">🏦</div><div><b>PROP FIRM DESK</b> · every bot has its own $${(r.size/1000)}k account<br>
    <span class="mu">📝 ${P.n_eval} in evaluation · 💼 ${P.n_funded} funded · 💀 ${P.n_out} blown & out</span><br>
    <span class="mu">Pass: 2 days of +$${r.eval_day.toLocaleString('en-GB')} · Out: a −$${r.dd.toLocaleString('en-GB')} day or a close at/below $${(r.size-r.dd).toLocaleString('en-GB')} · Funded goal: $${r.payday}+/day</span>
    ${B?`<br><span class="mu">The Boss's account: ${B.dead?'💀 blown on '+esc(B.dead_day):(B.phase==='funded'?'💼 funded':'📝 in evaluation')}</span>`:''}</div></div>`;
}
function card(f){
  const col = COL[f.cls]||'#888';
  const w = Math.min(100, Math.abs(f.pnl||0)/maxAbs*100);
  const tags = [];
  if (M.leader===f.name) tags.push(`<span class="tg q">👑 ${M.crown_needs_qual?'LEADER':'PROVISIONAL LEADER'}</span>`);
  if (f.qualified) tags.push('<span class="tg q">★ QUALIFIED</span>'); else tags.push('<span class="tg">UNPROVEN</span>');
  if (f.danger) tags.push('<span class="tg d">⚠ KO ZONE</span>');
  if (f.safe) tags.push('<span class="tg s">🛡 SAFE</span>');
  if (f.immune) tags.push(`<span class="tg n">🛡 GRACE · ${f.grace_left} more session${f.grace_left>1?'s':''}</span>`);
  if (f.status==='entering') tags.push('<span class="tg n">NEXT SESSION</span>');
  if (f.origin==='challenger' && !f.immune && f.status!=='entering') tags.push('<span class="tg n">CHALLENGER</span>');
  let pos = '';
  const op = f.opens||[];
  if (op.length===1 && !M.multi){ const o=op[0];
    pos = `<div class="mu" style="font-size:11.5px;margin-top:6px">In at <b style="color:#e9eefb">${num(o.entry)}</b> (${esc(o.since)})${o.stop?` · stop ${num(o.stop)}`:''}${o.target?` · target ${num(o.target)}`:''} · open <span class="${cls(o.upnl)}">${money(o.upnl)}</span></div>`; }
  else if (op.length){
    pos = `<div class="chips">${op.slice(0,6).map(o=>`<span class="chip"><span class="${o.side==='Long'?'up':'dn'}">${o.side==='Long'?'▲':'▼'}</span> ${esc(short(o.asset))} <span class="${cls(o.upnl)}">${money(o.upnl)}</span></span>`).join('')}${op.length>6?`<span class="chip">+${op.length-6}</span>`:''}</div>`; }
  return `<div class="card ${f.danger?'danger':''} ${M.leader===f.name?'lead':''}" data-n="${esc(f.name)}">
    <span class="lv px">LV ${f.level}</span>
    <div class="ch"><div class="av" style="background:${col}">${esc(ini(f.name))}</div>
      <div><div class="cn">${esc(f.name)}</div><div class="cl" style="color:${col}">${f.cls} · ${f.wins}W–${f.losses}L</div></div></div>
    <div class="row"><div><div class="pnl ${cls(f.pnl)}">${money(f.pnl)}</div><div class="mu" style="font-size:11px">today <span class="${cls(f.today)}">${money(f.today)}</span></div></div>
      <div style="text-align:right">${stance(f)}<div style="margin-top:6px">${spark(f.spark,90,24)}</div></div></div>
    <div class="bar"><i style="width:${w}%;background:${(f.pnl||0)>=0?'#2fe07a':'#ff4d5e'}"></i></div>
    ${f.status==='active'?propTag(f,true):''}
    ${pos}
    <div class="bub">💭 ${esc(f.thought)}</div>
    <div class="tags">${tags.join('')}</div></div>`;
}
function feedHTML(items){
  if(!items.length) return '<div class="empty">No action yet today.</div>';
  const ico={long:'🟢',short:'🔴',win:'💰',loss:'💥',ko:'☠️',join:'🚪',trophy:'🏆',info:'📣'};
  return items.map(e=>`<div class="ev k-${e.kind}"><div class="t">${esc(e.t)}</div><div>${ico[e.kind]||'•'} ${e.name?`<b>${esc(e.name)}</b> `:''}<span class="x">${esc(e.text)}</span></div></div>`).join('');
}
function chart(f, asset){
  const C = A.candles[asset]||[]; if(!C.length) return '<div class="empty">No bars yet today.</div>';
  const W=820,H=260,pad=46;
  let lo=Math.min(...C.map(c=>c[3])), hi=Math.max(...C.map(c=>c[2]));
  const op=(f&&f.opens||[]).filter(o=>o.asset===asset);
  op.forEach(o=>[o.stop,o.target,o.entry].forEach(v=>{if(v!=null){lo=Math.min(lo,v);hi=Math.max(hi,v);}}));
  const r=(hi-lo)||1; lo-=r*.05; hi+=r*.05;
  const y=v=>((hi-v)/(hi-lo)*(H-20)+10).toFixed(1);
  const n=Math.max(C.length, M.key==='crypto'?96:26), bw=(W-pad)/n, x=i=>(pad+i*bw+bw/2).toFixed(1);
  const ti={}; C.forEach((c,i)=>ti[c[0]]=i);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="background:#0d1426;border-radius:12px;border:1px solid #243050">`;
  for(let k=0;k<5;k++){const v=lo+(hi-lo)*k/4; s+=`<line x1="${pad}" x2="${W}" y1="${y(v)}" y2="${y(v)}" stroke="#1a2440"/><text x="2" y="${+y(v)+4}" fill="#8592b0" font-size="10">${v>=1000?Math.round(v):v.toFixed(2)}</text>`;}
  const step = n>40?12:4;
  C.forEach((c,i)=>{const col=c[4]>=c[1]?'#2fe07a':'#ff4d5e';
    s+=`<line x1="${x(i)}" x2="${x(i)}" y1="${y(c[2])}" y2="${y(c[3])}" stroke="${col}"/>`;
    s+=`<rect x="${(+x(i)-bw*.32).toFixed(1)}" width="${Math.max(1,bw*.64).toFixed(1)}" y="${y(Math.max(c[1],c[4]))}" height="${Math.max(1,Math.abs(y(c[1])-y(c[4]))).toFixed(1)}" fill="${col}" opacity=".85"/>`;
    if(i%step===0) s+=`<text x="${x(i)}" y="${H-1}" fill="#8592b0" font-size="9" text-anchor="middle">${c[0]}</text>`;});
  const vw=C.map((c,i)=>c[5]!=null?`${x(i)},${y(c[5])}`:null).filter(Boolean).join(' ');
  if(vw) s+=`<polyline points="${vw}" fill="none" stroke="#ffcc33" stroke-width="1.2" stroke-dasharray="4 3" opacity=".8"/>`;
  op.forEach(o=>{
    if(o.stop) s+=`<line x1="${pad}" x2="${W}" y1="${y(o.stop)}" y2="${y(o.stop)}" stroke="#ff4d5e" stroke-dasharray="6 4"/><text x="${W-4}" y="${+y(o.stop)-3}" fill="#ff4d5e" font-size="10" text-anchor="end">stop</text>`;
    if(o.target) s+=`<line x1="${pad}" x2="${W}" y1="${y(o.target)}" y2="${y(o.target)}" stroke="#2fe07a" stroke-dasharray="6 4"/><text x="${W-4}" y="${+y(o.target)-3}" fill="#2fe07a" font-size="10" text-anchor="end">target</text>`; });
  (f&&f.marks||[]).filter(m=>m.a===asset && ti[m.t]!=null && m.px!=null).forEach(m=>{
    const cx=x(ti[m.t]), cy=y(m.px);
    if(m.k==='in') s+= m.side>0 ? `<path d="M${cx} ${+cy+4} l-7 12 h14 z" fill="#2fe07a" stroke="#0a0e19"/>` : `<path d="M${cx} ${+cy-4} l-7 -12 h14 z" fill="#ff4d5e" stroke="#0a0e19"/>`;
    else s+=`<circle cx="${cx}" cy="${cy}" r="5" fill="#0a0e19" stroke="${(m.pnl||0)>0?'#2fe07a':'#ff4d5e'}" stroke-width="2.5"/>`; });
  s+=`<text x="${W-4}" y="14" fill="#ffcc33" font-size="10" text-anchor="end">--- VWAP</text></svg>`;
  return s;
}
let modalName=null;
function openModal(name, asset){
  const f = A.fighters.find(z=>z.name===name); if(!f) return;
  modalName = name;
  const assets = M.assets;
  if(!asset){ asset = (f.opens&&f.opens[0]&&f.opens[0].asset) || ((f.marks||[]).slice(-1)[0]||{}).a || assets[0]; }
  st.asset = asset;
  const q=f.qual||{}; const col=COL[f.cls];
  const tl = f.trades.length ? f.trades.map(t=>`<div class="tl"><b class="${cls(t.pnl)}">${money(t.pnl)}</b> · ${M.multi?`<b>${esc(short(t.asset))}</b> `:''}${t.side}${t.lots?` ${t.lots} lot${t.lots>1?'s':''}`:''} ${num(t.entry)} → ${num(t.exit)} <span class="mu">· ${esc(t.when)}</span><br><span class="mu">Why in:</span> ${esc(t.why)}<br><span class="mu">Why out:</span> ${esc(t.out)}</div>`).join('') : '<div class="empty">No finished trades in the arena yet.</div>';
  const ol = (f.opens||[]).length ? (f.opens||[]).map(o=>`<div class="tl"><b class="${o.side==='Long'?'up':'dn'}">${o.side==='Long'?'▲':'▼'} ${esc(o.asset)}${o.lots?` ×${o.lots}`:''}</b> in at ${num(o.entry)} (${esc(o.since)})${o.stop?` · stop ${num(o.stop)}`:''}${o.target?` · target ${num(o.target)}`:''} · open <b class="${cls(o.upnl)}">${money(o.upnl)}</b><br><span class="mu">Why:</span> ${esc(o.why)}</div>`).join('') : '<div class="mu" style="font-size:12px">No open positions.</div>';
  const abtn = assets.length>1 ? `<div style="margin:6px 0">${assets.map(a=>`<span class="abtn ${a===asset?'on':''}" data-asset="${esc(a)}">${esc(short(a))}</span>`).join('')}</div>` : '';
  document.getElementById('mbody').innerHTML = `
    <div class="ch"><div class="av" style="background:${col};flex-basis:54px;height:54px">${esc(ini(f.name))}</div>
      <div><div class="nm">${esc(f.name)}</div><div class="cl" style="color:${col}">${f.cls} · ${esc(f.family)} · level ${f.level}</div><div class="mu" style="margin-top:4px">${esc(f.about)}</div></div></div>
    <div class="bub" style="margin-top:14px">💭 ${esc(f.thought)}</div>
    <div class="kv">
      <div><span>Arena P&amp;L</span><b class="${cls(f.pnl)}">${money(f.pnl)}</b></div>
      <div><span>Today</span><b class="${cls(f.today)}">${money(f.today)}</b></div>
      <div><span>Record</span><b>${f.wins}W – ${f.losses}L</b></div>
      <div><span>Position</span><b>${stance(f)}</b></div>
      <div><span>Qualifying</span><b style="color:${q.ok?'#ffcc33':'#8592b0'}">${q.ok?'★ Passed':'Not passed'}</b></div>
      <div><span>Qual. net</span><b class="${cls(q.net)}">${money(q.net)}</b></div>
      <div><span>1st / 2nd half</span><b style="font-size:13px;white-space:nowrap"><span class="${cls(q.h1)}">${money(q.h1)}</span> / <span class="${cls(q.h2)}">${money(q.h2)}</span></b></div>
      <div><span>Sharpe / PF</span><b>${q.sharpe??'–'} / ${q.pf??'–'}</b></div>
    </div>
    <h4 class="px" style="font-size:9px;color:#8592b0">📜 RULEBOOK · how this strategy trades</h4>
    <div class="rulebook"><ul style="margin:0;padding-left:18px">${(f.rules||[]).map(r=>`<li>${esc(r)}</li>`).join('')}</ul>
      <div style="margin-top:8px;font-size:12px">${f.code?`<a href="${esc(f.code)}" target="_blank" rel="noopener" style="color:#3ef0ff">View the exact code on GitHub ↗</a> · `:''}<span class="mu">Want it in TradingView? Once it wins, it can be rewritten in Pine Script.</span></div></div>
    <h4 class="px" style="font-size:9px;color:#8592b0">OPEN POSITIONS</h4>${ol}
    <h4 class="px" style="font-size:9px;color:#8592b0;margin-top:14px">TODAY'S BATTLEFIELD · ${esc(M.cur_day)} (UK times)</h4>${abtn}${chart(f, asset)}
    <div class="mu" style="font-size:11px;margin:6px 0 14px">▲/▼ = entries, ○ = exits. Dashed lines = live stop and target.</div>
    <h4 class="px" style="font-size:9px;color:#8592b0">RECENT FIGHTS</h4>${tl}`;
  R.querySelector('.modal').classList.add('on');
}
function sorted(list){
  const a=[...list];
  if(st.sort==='today') a.sort((p,q)=>(q.today||0)-(p.today||0));
  else if(st.sort==='name') a.sort((p,q)=>p.name.localeCompare(q.name));
  else a.sort((p,q)=>(q.pnl||0)-(p.pnl||0));
  return a;
}
function view(){
  const act = A.fighters.filter(f=>f.status==='active'||f.status==='entering');
  let list = sorted(act);
  if(st.filter==='trade') list = list.filter(f=>(f.opens||[]).length);
  if(st.filter==='danger') list = list.filter(f=>f.danger);
  if(st.filter==='qual') list = list.filter(f=>f.qualified);
  if(st.tab==='arena'){
    const b=k=>`<button data-sort="${k}" class="${st.sort===k?'on':''}">`, fb=k=>`<button data-filter="${k}" class="${st.filter===k?'on':''}">`;
    return `<div class="wrap"><div>
      <div class="ctl">${b('pnl')}Sort: Arena P&amp;L</button>${b('today')}Today</button>${b('name')}Name</button>
      <span style="width:10px"></span>${fb('all')}All</button>${fb('trade')}In a trade</button>${fb('danger')}KO zone</button>${fb('qual')}Qualified</button></div>
      <div class="grid">${list.map(card).join('') || '<div class="empty">Nobody matches this filter.</div>'}</div></div>
      <div class="box"><h4 class="px">⚔ BATTLE FEED</h4><div class="feed">${feedHTML(A.feed)}</div></div></div>`;
  }
  if(st.tab==='board'){
    const all = [...A.fighters].sort((p,q)=>(q.pnl||0)-(p.pnl||0));
    return `<div class="box tw"><table><tr><th>#</th><th>Fighter</th><th>Class</th><th>Arena P&amp;L</th><th>Today</th><th>W–L</th><th>Level</th><th>Status</th><th>Now</th><th>Season</th></tr>
      ${all.map((f,i)=>`<tr style="cursor:pointer" data-n="${esc(f.name)}"><td>${i+1}</td><td>${M.leader===f.name?'👑 ':''}${esc(f.name)} ${f.qualified?'<span style="color:#ffcc33">★</span>':''}</td><td style="color:${COL[f.cls]}">${f.cls}</td>
      <td class="${cls(f.pnl)}">${money(f.pnl)}</td><td class="${cls(f.today)}">${money(f.today)}</td><td>${f.wins}–${f.losses}</td><td>${f.level}</td>
      <td>${f.status==='ko'?'<span class="dn">K.O.</span>':f.danger?'<span class="dn">KO zone</span>':f.safe?'<span class="up">Safe</span>':f.status}</td><td>${stance(f)}</td><td>${spark(f.spark,90,22)}</td></tr>`).join('')}
      <tr><td></td><td class="mu"><i>The Boss: ${esc(A.boss.name)}</i></td><td class="mu">Boss</td><td class="${cls(A.boss.pnl)}">${money(A.boss.pnl)}</td><td class="${cls(A.boss.today)}">${money(A.boss.today)}</td><td colspan="5" class="mu" style="text-align:left">benchmark, can't be knocked out</td></tr></table></div>`;
  }
  if(st.tab==='grave'){
    const g = A.fighters.filter(f=>f.status==='ko');
    if(!g.length) return `<div class="box empty">☠️ The graveyard is empty. The first knockouts happen at ${esc(M.ko_time)}.</div>`;
    return `<div class="grid">${g.map(f=>`<div class="card" data-n="${esc(f.name)}" style="opacity:.8"><div class="ch"><div class="av" style="background:#3a2030;color:#ff4d5e">☠</div><div><div class="cn">${esc(f.name)}</div><div class="cl">${f.cls} · KO ${esc(f.ko_day)}</div></div></div><div class="row"><div class="pnl ${cls(f.pnl)}">${money(f.pnl)}</div><div class="mu">${f.wins}W–${f.losses}L · lasted ${f.level-1} session(s)</div></div></div>`).join('')}</div>`;
  }
  if(st.tab==='queue'){
    if(!A.queue.length) return '<div class="box empty">The challenger pool is empty. Every challenger has had its shot.</div>';
    return `<div class="box tw"><div class="mu" style="margin-bottom:8px">Waiting in the tunnel. When fighters get knocked out, the best <b>qualified</b> challengers (highest Sharpe) take their seats. Qualifying = last ${M.qual_sessions} sessions, at least 10 trades, profitable in both halves, profit factor ≥ 1.1.</div>
      <table><tr><th>#</th><th>Challenger</th><th>Class</th><th>Qual. net</th><th>1st half</th><th>2nd half</th><th>Trades</th><th>Win</th><th>PF</th><th>Sharpe</th><th>Ready?</th></tr>
      ${A.queue.map((c,i)=>{const q=c.qual;return `<tr><td>${i+1}</td><td title="${esc(c.about)}">${esc(c.name)}</td><td style="color:${COL[c.cls]}">${c.cls}</td><td class="${cls(q.net)}">${money(q.net)}</td><td class="${cls(q.h1)}">${money(q.h1)}</td><td class="${cls(q.h2)}">${money(q.h2)}</td><td>${q.trades}</td><td>${q.win!=null?Math.round(q.win*100)+'%':'–'}</td><td>${q.pf??'–'}</td><td>${q.sharpe??'–'}</td><td>${q.ok?'<span class="up">★ ready</span>':'<span class="mu">not yet</span>'}</td></tr>`}).join('')}</table></div>`;
  }
  if(st.tab==='trophy'){
    if(!A.trophies.length) return `<div class="box empty">🏆 No trophies yet. The first weekly champion is crowned after 5 sessions.</div>`;
    return `<div class="grid">${A.trophies.map(t=>`<div class="box crown"><h4 class="px">🏆 WEEK ${t.week}</h4><div class="nm">${esc(t.name||'No champion')}</div><div class="big ${cls(t.pnl)}">${t.name?money(t.pnl):''}</div><div class="mu">${esc(t.start)} → ${esc(t.end)} · Boss made ${money(t.boss)}</div></div>`).join('')}</div>`;
  }
  if(st.tab==='chatter'){
    const rb = (A.reddit||[]);
    const hl = (A.headlines||[]);
    if(A.reddit===undefined){
      return `<div class="box"><h4 class="px">🌍 WORLD NEWS & BIG NAMES</h4><div class="mu" style="font-size:11.5px;margin-bottom:6px">What the News fighters read: Trump, the Fed, world events and the big CEOs. Each headline only counts from the moment it was first seen.</div>${hl.length?hl.map(h=>`<div class="hl"><span class="mu">${esc(h.t)}</span><b>${esc(h.asset)}</b><span>${esc(h.title)}</span><b class="${cls(h.sent)}">${h.sent>0?'+':''}${h.sent}</b></div>`).join(''):'<div class="empty">No headlines yet. They build up every time the city updates.</div>'}
        <div class="mu" style="font-size:11px;margin-top:8px">Mood score: −1 very negative … +1 very positive, from the headline wording.</div></div>`;
    }
    return `<div class="two"><div class="box"><h4 class="px">👽 REDDIT RIGHT NOW</h4>
      ${rb.length?`<table><tr><th>#</th><th>Stock</th><th>Rank</th><th>Mentions</th><th>24h ago</th><th>Change</th></tr>${rb.map((r,i)=>`<tr><td>${i+1}</td><td><b>${esc(r.asset)}</b></td><td>#${r.rank}</td><td>${r.mentions}</td><td>${r.prev??'–'}</td><td class="${cls((r.prev!=null)?r.mentions-r.prev:0)}">${r.prev?((r.mentions/r.prev-1)*100).toFixed(0)+'%':'–'}</td></tr>`).join('')}</table>`:'<div class="empty">No Reddit data yet. It builds up every time the hub runs.</div>'}</div>
      <div class="box"><h4 class="px">📰 LATEST HEADLINES</h4>${hl.length?hl.map(h=>`<div class="hl"><span class="mu">${esc(h.t)}</span><b>${esc(h.asset)}</b><span>${esc(h.title)}</span><b class="${cls(h.sent)}">${h.sent>0?'+':''}${h.sent}</b></div>`).join(''):'<div class="empty">No headlines yet.</div>'}
      <div class="mu" style="font-size:11px;margin-top:8px">Mood score: −1 very negative … +1 very positive, from the headline wording.</div></div></div>`;
  }
  if(st.tab==='rules'){
    return `<div class="box rules"><h4 class="px">HOW THE ${esc(M.title.toUpperCase())} WORKS</h4><ul>
      <li><b>Sizing:</b> ${esc(M.sizing)}</li>
      <li><b>No cheating:</b> every decision is made at a bar's close and filled at the next bar's open. The bar still forming is ignored.${M.key==='hype'?' Headlines and Reddit numbers are only used after they were published.':''}</li>
      <li><b>As many trades as the setup allows:</b> after an exit, a fighter can go again whenever its setup shows up again. Every trade pays costs, so over-trading hurts.</li>
      ${A.prop?'':`<li><b>Fair knockouts:</b> at ${esc(M.ko_time)} up to ${M.ko_per_day} fighters are knocked out, the worst first, but only if they are losing overall <i>and</i> lost money over their last 3 sessions. Every fighter gets ${M.grace} sessions' grace before it can be knocked out.</li>`}
      <li><b>🐒 The Monkey team:</b> 20 monkeys trade at random with the same costs. A strategy that can't beat 75% of them is probably just lucky, so it can't win the Finals.</li>
      ${A.prop?`<li><b>🏦 Prop firm:</b> every bot trades its own $${A.prop.rules.size.toLocaleString('en-GB')} account. <b>Evaluation:</b> pass with 2 days that each close at +$${A.prop.rules.eval_day.toLocaleString('en-GB')} or more (they don't have to be in a row). <b>Funded:</b> after passing it gets a fresh $${A.prop.rules.size.toLocaleString('en-GB')} account; the goal is at least $${A.prop.rules.payday} a day. <b>Out:</b> checked at the close of each day (not trailing): if the day lost $${A.prop.rules.dd.toLocaleString('en-GB')} or more, <i>or</i> the balance closes at or below $${(A.prop.rules.size-A.prop.rules.dd).toLocaleString('en-GB')}, the account is blown and the bot leaves the tower for good. Dips during the day don't count. Its seat goes to a new challenger with a fresh evaluation.</li>
      <li><b>🤖 The bot's own safety rules:</b> up to ${A.prop.rules.max_lots} NQ minis per trade, fewer when it's close to a limit (3 lots with more than $1,500 of room, 2 with $1,000–1,500, 1 below that; room = distance to the nearer of the two limits). <b>Daily stop:</b> after losing $${A.prop.rules.daily_stop} in a day it goes flat until tomorrow. <b>Daily goal:</b> in the evaluation it banks the day once it's +$${A.prop.rules.eval_day.toLocaleString('en-GB')}. Funded bots keep trading after $${A.prop.rules.payday}; the card also shows what would have happened if they stopped at $${A.prop.rules.payday}. To win the Nasdaq finals a bot must have passed the evaluation.</li>`:''}
      <li><b>🏆 Finals podium:</b> when the final bell rings, the best 3 fighters in profit make the podium (🥇🥈🥉) and are kept for paper trading. They are ranked by how many finals checks they pass, then by profit. 🥇 is a full champion only if it passes every check.</li>
      <li><b>New challengers:</b> empty seats go first to challengers that pass qualifying (last ${M.qual_sessions} sessions, at least 10 trades, profitable in both halves, profit factor ≥ 1.1). If not enough qualify, the best of the rest come in <i>on trial</i>.</li>
      ${A.prop?'':`<li><b>Comebacks:</b> knocked-out fighters return to the waiting room after 5 sessions and can fight their way back.</li>`}
      <li><b>Leader 👑:</b> ${M.crown_needs_qual?'the qualified fighter with the highest arena P&amp;L.':'social data has no long history to qualify on yet, so the crown is provisional: the best fighter in profit.'}</li>
      <li><b>The Boss:</b> ${esc(A.boss.name)} is the benchmark to beat.</li>
      <li class="mu">A testing lab, not trading advice. Paper results ignore real-world issues like partial fills and fast markets.</li></ul></div>`;
  }
  return '';
}
function hero(){
  const L = A.fighters.find(f=>f.name===M.leader);
  const lead = L ? `<div class="box crown"><h4 class="px">👑 ${M.crown_needs_qual?'LEADER':'PROVISIONAL LEADER'}</h4><div class="nm">${esc(L.name)}</div>
      <div class="big ${cls(L.pnl)}">${money(L.pnl)}</div><div class="mu">${L.cls} · ${L.wins}W–${L.losses}L · ${stance(L)}</div>
      <div class="bub">💭 ${esc(L.thought)}</div></div>`
    : `<div class="box crown"><h4 class="px">👑 LEADER</h4><div class="nm">${M.started?'Throne is empty':'Season starts '+esc(M.season_start)}</div>
      <div class="mu" style="margin-top:6px">${M.started?(M.crown_needs_qual?'No qualified fighter is in profit yet.':'Nobody is in profit yet.'):'Fighters are warming up. The live season begins at the first session.'}${M.top_raw&&M.started?' Top raw score: <b>'+esc(M.top_raw)+'</b>.':''}</div></div>`;
  const beat = L ? ((L.pnl||0) > (A.boss.pnl||0) ? '<span class="up">Leader is beating the Boss</span>' : '<span class="dn">The Boss is winning</span>') : '';
  return `<div class="hero">${lead}
    <div class="box"><h4 class="px">🗿 THE BOSS</h4><div class="nm">${esc(A.boss.name)}</div><div class="big ${cls(A.boss.pnl)}">${money(A.boss.pnl)}</div><div class="mu">today <span class="${cls(A.boss.today)}">${money(A.boss.today)}</span> · ${beat}</div></div>
    <div class="box"><h4 class="px">🏟 SEASON</h4><div class="nm">${M.started?`Day ${M.day_n} · Week ${M.week_n}`:'Pre-season'}</div>
      <div class="mu" style="margin-top:6px">${M.n_active} fighting · ${M.n_ko} knocked out · ${M.pool_left} waiting</div>
      <div class="mu">${M.live?`Next knockouts at <b style="color:#ff4d5e">${esc(M.ko_time)}</b>`:`Next session opens <b style="color:#e9eefb">${esc(M.next_open)} UK</b>`}</div></div></div>`;
}
function switcher(){
  return `<div class="switch">${D.order.map(k=>{const a=D.arenas[k], m=a.meta; const L=a.fighters.find(f=>f.name===m.leader);
    return `<div class="sw ${k===st.arena?'on':''}" data-arena="${k}"><div class="t1">${m.icon} ${esc(m.title)}</div>
      <div class="t2"><span class="dot ${m.live?'on':''}"></span>${m.live?'LIVE':'closed'} · ${m.n_active} fighters</div>
      <div class="t2">👑 ${L?esc(L.name)+' '+money(L.pnl):'no leader yet'}</div></div>`;}).join('')}</div>`;
}
function ticker(){
  if(!M.multi){ const t=M.tick[0]; return `<div class="ticker"><b>${num(t.price)}</b><div class="${cls(t.chg_pct)}">${t.chg_pct>0?'+':''}${t.chg_pct}% today</div></div>`; }
  return `<div class="tickrow">${M.tick.map(t=>`<span>${esc(short(t.a))} <b>${num(t.price)}</b> <span class="${cls(t.chg_pct)}">${t.chg_pct>0?'+':''}${t.chg_pct}%</span></span>`).join('')}</div>`;
}
// ======================= CITY + TOWERS =======================
const TOWER = {nq:{c:'#3ea8ff',g:'#123a66',name:'NASDAQ TOWER'}, stocks:{c:'#2fe07a',g:'#0f4a33',name:'STOCK EXCHANGE'},
               crypto:{c:'#ffb020',g:'#5a3a08',name:'CRYPTO HQ'}, hype:{c:'#ff3ea5',g:'#5a1238',name:'HYPE STUDIO'}};
function hsh(s){let h=0; for(const ch of String(s)) h=(h*31+ch.charCodeAt(0))|0; return Math.abs(h);}
const SKIN=['#f5d0a9','#e0ac69','#c68642','#8d5524','#f1c27d','#ffdbac'], HAIR=['#2b1b10','#5a3a1a','#c9a227','#111','#8a2a1a','#d9d9d9','#3b2f63'];
function guy(f, extra=''){
  const h=hsh(f.name), col=COL[f.cls]||'#888';
  return `<div class="guy ${extra}" style="--skin:${SKIN[h%SKIN.length]};--hair:${HAIR[(h>>3)%HAIR.length]};--c:${col}">
    <i class="hair"></i><i class="head"></i><i class="body"></i><i class="arm l"></i><i class="arm r"></i></div>`;
}
function fState(f, live){
  const op=(f.opens||[]).length;
  if(f.status==='ko') return 'ko';
  if(f.status==='entering') return 'entering';
  if(f.danger) return 'danger';
  if(op) return 'trading';
  if(!live) return 'sleep';
  return 'idle';
}
function windowsOf(a){
  const live=a.meta.live; const f=a.fighters.filter(x=>x.status!=='ko');
  return f.map(x=>{const s=fState(x,live); const c = s==='danger'?'w-red':s==='trading'?'w-gold':s==='entering'?'w-cyan':s==='sleep'?((x.pnl||0)>0?'w-dimg':'w-dim'):((x.pnl||0)>0?'w-green':(x.pnl||0)<0?'w-pink':'w-on');
    return `<i class="win ${c}" title="${esc(x.name)} ${money(x.pnl)}"></i>`;}).join('');
}
function towerHTML(k, i){
  const a=D.arenas[k], m=a.meta, T=TOWER[k]||TOWER.nq, L=a.fighters.find(f=>f.name===m.leader);
  const n=a.fighters.filter(x=>x.status!=='ko').length, rows=Math.ceil(n/4), hgt=Math.max(150, rows*22+70);
  const ko=a.fighters.filter(f=>f.status==='ko').length;
  return `<div class="tw-wrap" data-tower="${k}">
    <div class="neon" style="--c:${T.c}">${m.icon} ${T.name}</div>
    <div class="tower" style="--c:${T.c};--g:${T.g};height:${hgt}px">
      <i class="antenna ${m.live?'on':''}"></i>
      <div class="bill">${L?`👑 ${esc(L.name)}<br><b class="${cls(L.pnl)}">${money(L.pnl)}</b>`:'👑 throne empty'}</div>
      <div class="wins">${windowsOf(a)}</div>
      <div class="door"><span>${m.live?'OPEN':'CLOSED'}</span></div>
    </div>
    <div class="tw-info"><b>${esc(m.title)}</b> <span class="dot ${m.live?'on':''}"></span>${m.live?'live':'closed'}<br>
      <span class="mu">${n} inside · ☠ ${ko} · Boss <span class="${cls(a.boss.pnl)}">${money(a.boss.pnl)}</span></span><br>
      <span class="mu">🐒 monkeys ${money((a.monkeys||{}).median)}</span>${a.prop?`<br><span class="mu">💼 ${a.prop.n_funded} funded · 📝 ${a.prop.n_eval} in eval</span>`:''}</div>
  </div>`;
}
function hallOfFame(){
  const fr=D.frozen; if(!fr||!fr.leagues) return '';
  const M=['🥇','🥈','🥉'];
  const rows=D.order.map(k=>{ const F=fr.leagues[k]; if(!F) return ''; const a=D.arenas[k];
    const P=F.podium||[F.winner,...(F.runners||[])].filter(Boolean);
    return P.map((r,i)=>{ const f=a.fighters.find(x=>x.name===r.name); const since=f?(f.pnl||0)-(r.pnl||0):null;
      const st=!f?'gone':f.status==='ko'?'💀 out':(f.prop&&f.prop.dead?'💀 blown':'✅ still running');
      return `<div class="hof-r"><span>${a.meta.icon} ${M[i]} <b data-k="${k}" data-n="${esc(r.name)}" class="lnk">${esc(r.name)}</b></span><span>at finals <span class="${cls(r.pnl)}">${money(r.pnl)}</span> · since <span class="${cls(since)}">${since==null?'–':money(since)}</span> · ${st}</span></div>`; }).join(''); }).join('');
  return `<div class="finals hof"><div class="px" style="font-size:10px;color:#7fd8ff;margin-bottom:8px;line-height:1.6">🏛 HALL OF FAME · the podium keeps trading after the finals, so we can see if it was skill or luck</div>${rows||'<div class="mu">Nobody made the podium.</div>'}</div>`;
}
function cityMoney(){
  const out={today:0, month:0, per:[], best:null, worst:null};
  D.order.forEach(k=>{ const a=D.arenas[k]; if(a.prop) return; const act=a.fighters.filter(f=>f.status==='active');
    const t=act.reduce((s,f)=>s+(f.today||0),0), m=act.reduce((s,f)=>s+(f.month!=null?f.month:(f.pnl||0)),0);
    out.today+=t; out.month+=m; out.per.push({k, a, t, m, n:act.length});
    act.forEach(f=>{ if(!out.best||(f.today||0)>(out.best.f.today||0)) out.best={f,k}; if(!out.worst||(f.today||0)<(out.worst.f.today||0)) out.worst={f,k}; }); });
  return out;
}
function billboard(){
  const C=cityMoney(), mon=new Date().toLocaleString('en-GB',{month:'long'}).toUpperCase();
  const big = x => `<b class="led ${x>0?'g':x<0?'r':''}">${money(x)}</b>`;
  const per = C.per.map(p=>`<span class="bb-t">${p.a.meta.icon} ${esc((TOWER[p.k]||{}).name||p.a.meta.title)} <i class="${cls(p.t)}">${money(p.t)}</i> <em>· ${mon.slice(0,3)} <i class="${cls(p.m)}">${money(p.m)}</i></em></span>`).join('');
  const crawl = [C.best&&`🔥 TOP EARNER TODAY: ${C.best.f.name} ${money(C.best.f.today)}`, C.worst&&(C.worst.f.today||0)<0&&`🧊 ROUGHEST DAY: ${C.worst.f.name} ${money(C.worst.f.today)}`,
                 ...C.per.map(p=>`${p.a.meta.icon} ${p.a.meta.title.toUpperCase()}: ${p.n} BOTS · TODAY ${money(p.t)} · ${mon} ${money(p.m)}`)].filter(Boolean)
                 .map(x=>`<span>${esc(x)}</span>`).join('<span class="sep">★</span>');
  return `<div class="tsq"><i class="bulbs"></i>
    <div class="bb-h px">📺 STRATEGY CITY SQUARE · ALL BOTS COMBINED</div>
    <div class="bb-screens">
      <div class="bb-s"><div class="bb-l px">TODAY</div>${big(C.today)}</div>
      <div class="bb-s"><div class="bb-l px">${mon}</div>${big(C.month)}</div>
    </div>
    <div class="bb-per">${per}</div>
    <div class="bb-crawl"><div class="bb-in">${crawl}${crawl?'<span class="sep">★</span>'+crawl:''}</div></div>
    <div class="bb-note">Adds up every bot still in the game in the Stock, Crypto and Hype towers. The Nasdaq tower runs as separate prop-firm accounts, so it isn't added here: see its own tower.</div>
  </div>`;
}
function cityView(){
  const stars=Array.from({length:70},(_,i)=>`<i class="star" style="left:${((i*61.803)%100).toFixed(1)}%;top:${((i*37.17+i*i*0.7)%55).toFixed(1)}%;animation-delay:${(i%7)/2}s"></i>`).join('');
  const feed=D.order.flatMap(k=>D.arenas[k].feed.slice(0,8).map(e=>({...e,k}))).slice(0,30);
  const tape=feed.map(e=>`<span>${D.arenas[e.k].meta.icon} <b>${esc(e.name)}</b> ${esc(e.text)}</span>`).join('<span class="sep">◆</span>');
  const graves=D.order.flatMap(k=>D.arenas[k].fighters.filter(f=>f.status==='ko').map(f=>({f,k})));
  return `<div class="city">
    <div class="sky">${stars}<i class="moon"></i><div class="far"></div></div>
    <div class="city-title px">STRATEGY CITY</div>
    <div style="position:relative;margin-top:10px">${countdown()}</div>
    ${billboard()}
    <div class="city-sub">Tap a tower to go inside. Lit windows are fighters: <i class="win w-gold"></i> in a trade · <i class="win w-green"></i> in profit · <i class="win w-pink"></i> losing · <i class="win w-red"></i> KO zone · <i class="win w-cyan"></i> arriving</div>
    <div class="towers">${D.order.map(towerHTML).join('')}</div>
    <div class="street"><div class="tape"><div class="tape-in">${tape||'<span>Quiet night in the city.</span>'}</div></div></div>
    ${finalsPanel()}
    ${hallOfFame()}
    <div class="yard"><div class="yard-t px">☠ CEMETERY · ${graves.length}</div><div class="stones">${graves.slice(0,40).map(g=>`<div class="stone" data-k="${g.k}" data-n="${esc(g.f.name)}" title="${esc(g.f.name)} · ${money(g.f.pnl)}"><span>RIP</span><small>${esc(g.f.name.split(' ')[0])}</small></div>`).join('')||'<span class="mu">No graves yet.</span>'}</div></div>
    <div class="mu" style="font-size:11px;margin-top:8px;text-align:center">Updated ${esc(D.arenas[D.order[0]].meta.updated)} UK${D.reload?` · refreshes itself every few minutes`:''}</div>
  </div>`;
}
function desk(f, live, leader){
  const s=fState(f, live); const op=f.opens||[];
  const mon = op.length>1 ? `<b style="color:#3ef0ff">${op.length}</b>` : op.length ? (op[0].side==='Long'?'<b class="up">▲</b>':'<b class="dn">▼</b>') : (s==='sleep'?'<b class="mu">–</b>':'<i class="pulse"></i>');
  const badge = (f.name===leader?'<span class="crown">👑</span>':'') + (s==='danger'?'<span class="fx sweat">💦</span>':'') + (s==='sleep'?'<span class="fx zz">z<small>z</small></span>':'')
    + ((f.today||0)>0 && s!=='sleep'?'<span class="fx cash">💰</span>':'') + (f.immune?'<span class="fx">✨</span>':'');
  return `<div class="desk s-${s}" data-n="${esc(f.name)}">
    ${s==='danger'?'<i class="lamp"></i>':''}
    <div class="bubble">${esc(f.thought)}</div>
    <div class="station">${guy(f, s)}${badge}<div class="monitor">${mon}</div><div class="table"></div></div>
    <div class="plate"><span class="pn">${esc(f.name)}</span><b class="${cls(f.pnl)}">${money(f.pnl)}</b></div></div>`;
}
// ======================= GAME LOBBY: apartments with moving residents =======================
function where(f, live){
  const op=(f.opens||[]).length;
  if(op) return 'desk';            // in a trade: at the computer
  if(f.danger) return 'panic';     // in the KO zone: pacing the trading room
  if(!live) return 'bed';          // market closed: asleep
  return 'lounge';                 // market open, waiting for a setup: hanging out
}
function sprite(f, j, live, leader, roomX){
  const w=where(f, live); const op=f.opens||[];
  const desks=roomX.desks, beds=roomX.beds;
  let x, kls='', range='', dur=2.4;
  if(w==='desk'){ x=desks[j%desks.length]-1.6; kls='sit d'+(j%desks.length); }
  else if(w==='bed'){ x=beds[j%beds.length]; kls='sleep'; }
  else if(w==='panic'){ x=roomX.office[0]+Math.random()*(roomX.office[1]-roomX.office[0]); kls='wander panic'; range=roomX.office.join(','); dur=1.0; }
  else { x=roomX.lounge[0]+Math.random()*(roomX.lounge[1]-roomX.lounge[0]); kls='wander'; range=roomX.lounge.join(','); dur=2.4; }
  const chip = op.length ? `<span class="chip2 ${cls(op.reduce((a,o)=>a+(o.upnl||0),0))}">${op.length>1?op.length+' open ':''}${op.length===1?(op[0].side==='Long'?'▲ ':'▼ ')+esc(short(op[0].asset))+(op[0].lots?'×'+op[0].lots:''):''} ${money(op.reduce((a,o)=>a+(o.upnl||0),0))}</span>` : '';
  const fx = (f.name===leader?'<span class="crown2">👑</span>':'') + (w==='panic'?'<span class="sweat2">💦</span>':'') + (w==='bed'?'<span class="zz2">z<small>z</small>z</span>':'')
           + ((f.today||0)>0 && w!=='bed'?'<span class="cash2">💰</span>':'') + (f.immune?'<span class="new2">✨</span>':'') + (f.prop&&f.prop.phase==='funded'?'<span class="fund2">💼</span>':'');
  if(j%2) kls+=' alt';
  return `<div class="sp ${kls} w-${w}" data-n="${esc(f.name)}" data-range="${range}" data-dur="${dur}" style="left:${x}%;--dur:${dur}s">
    <div class="bub2"><b>${esc(f.name)}</b> <span class="${cls(f.pnl)}">${money(f.pnl)}</span> <span class="mu">· today</span> <span class="${cls(f.today)}">${money(f.today)}</span><br>${esc(f.thought)}</div>
    <div class="tag2 ${cls(f.pnl)}">${esc(f.name.length>16?f.name.slice(0,15)+'…':f.name)}</div>${chip}${fx}
    ${guy(f, '')}<i class="legs"><i></i><i></i></i></div>`;
}
const ROOMX = {desks:[8,17,26,35], beds:[73.5,80.5,87.5,94.5], office:[5,37], lounge:[44,66]};
function furniture(live, danger, penthouse){
  const desks=(penthouse?[ROOMX.desks[0]]:ROOMX.desks).map(x=>`<div class="dk" style="left:${x-3.6}%"><i class="scr"></i></div>`).join('');
  const beds=(penthouse?[ROOMX.beds[0]]:ROOMX.beds).map(x=>`<div class="bd2" style="left:${x-3}%"><i class="pil"></i><i class="blk"></i></div>`).join('');
  return `<div class="room r-office ${danger?'alarm':''}"><span class="rl">💹 TRADING ROOM</span><i class="wnd"></i><i class="wnd w2"></i>${danger?'<i class="siren"></i>':''}</div>
    <div class="room r-lounge"><span class="rl">☕ LOUNGE</span><i class="sofa"></i><i class="tv"></i><i class="coffee"></i><i class="plant"></i></div>
    <div class="room r-bed"><span class="rl">🛏 ${penthouse?'SUITE':'BEDROOMS'}</span><i class="wnd"></i></div>
    <div class="furn">${desks}${beds}</div>`;
}
function apartment(group, num, live, leader, penthouse){
  const danger=group.some(f=>f.danger);
  return `<div class="apt ${live?'day':'night'} ${penthouse?'pent':''}">
    <div class="fnum2 px">${penthouse?'👑':num}</div>
    <div class="aptR"><div class="rooms2">${furniture(live, danger, penthouse)}${group.map((f,j)=>sprite(f,j,live,leader,ROOMX)).join('')}</div>
    <div class="ledger">${group.map(f=>`<div class="lg" data-n="${esc(f.name)}"><span class="lg-n">${esc(f.name)}</span><span class="lg-v"><b class="${cls(f.pnl)}">${money(f.pnl)}</b> <em>total</em> · <b class="${cls(f.today)}">${money(f.today)}</b> <em>today</em></span>${propTag(f,false)}</div>`).join('')}</div></div></div>`;
}
function countdown(){
  if(!D.final_at) return '';
  return `<div class="finalbar"><span class="px">🏆 FINAL BELL</span> <b id="cd">…</b> <span class="mu">· ${new Date(D.final_at).toLocaleString('en-GB',{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}</span></div>`;
}
function tickCountdown(){
  const el=document.getElementById('cd'); if(!el||!D.final_at) return;
  const ms=new Date(D.final_at)-new Date();
  if(ms<=0){ el.textContent = D.frozen ? 'WINNERS CROWNED' : 'deciding the winners…'; return; }
  const d=Math.floor(ms/864e5), h=Math.floor(ms%864e5/36e5), m=Math.floor(ms%36e5/6e4), s=Math.floor(ms%6e4/1e3);
  el.textContent=`${d}d ${String(h).padStart(2,'0')}h ${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s`;
}
function finalsPanel(){
  const fr = D.frozen;
  const LBL = F => ({qualified:'passed the pre-season test',profit:'in profit',consistent:'up most days',risk:'worst day > −$'+F.risk_limit,trades:'3+ trades',monkeys:'beats 75% of monkeys',funded:'passed the prop evaluation'});
  const row = k => { const a=D.arenas[k], fz=fr&&fr.leagues&&fr.leagues[k], F=fz||a.finals; if(!F) return '';
    const P = F.podium || [F.winner, ...(F.runners||[])].filter(Boolean);
    const M = ['🥇','🥈','🥉'], lb=LBL(F);
    const chk = r => Object.entries(r.checks).map(([n,v])=>`<span class="ck ${v?'ok':'no'}">${v?'✓':'✗'} ${lb[n]}</span>`).join('');
    const steps = P.map((r,i)=>`<div class="pod p${i+1}">
        <div class="pod-l"><span class="medal">${M[i]}</span><b data-k="${k}" data-n="${esc(r.name)}" class="lnk">${esc(r.name)}</b></div>
        <div class="pod-r"><span class="${cls(r.pnl)}">${money(r.pnl)}</span> <span class="okn ${r.passed?'all':''}">${r.passed?'✅ all checks':r.n_ok+'/'+(F.n_checks||6)+' checks'}</span></div>
        ${i===0?`<div class="cks">${chk(r)}</div>`:''}</div>`).join('');
    const champ = P[0] && P[0].passed;
    return `<div class="fin"><div class="fin-h">${a.meta.icon} <b>${esc(a.meta.title)}</b> ${fz?'<span class="px" style="font-size:8px;color:#ffcc33">FINAL</span>':'<span class="mu" style="font-size:10.5px">· if it ended now</span>'}</div>
      ${P.length?steps:`<div class="mu">${fz?'Nobody finished in profit: empty podium.':'Nobody is in profit yet.'}</div>`}
      ${P.length?`<div class="mu" style="font-size:10.5px;margin-top:6px">${champ?(fz?'🏆 Champion passed every check.':'🏆 #1 passes every check right now.'):(fz?'No one passed every check, so no full champion. The 3 above are still kept.':'#1 still needs to pass every check to be a full champion.')}</div>`:''}</div>`; };
  return `<div class="finals"><div class="px" style="font-size:10px;color:#ffcc33;margin-bottom:8px;line-height:1.6">🏆 THE FINALS · the best 3 in each tower make the podium and get kept · ✅ = passed every check, including beating the 🐒 monkeys</div>
    <div class="fin-grid">${D.order.map(row).join('')}</div></div>`;
}
function towerView(){
  const k=st.arena, a=A, m=M, T=TOWER[k]||TOWER.nq, live=m.live;
  const inside=a.fighters.filter(f=>f.status==='active').sort((p,q)=>(q.pnl||0)-(p.pnl||0));
  const arriving=a.fighters.filter(f=>f.status==='entering');
  const L=inside.find(f=>f.name===m.leader);
  const rest=inside.filter(f=>f!==L);
  const groups=[]; for(let i=0;i<rest.length;i+=4) groups.push(rest.slice(i,i+4));
  const graves=a.fighters.filter(f=>f.status==='ko');
  const nDesk=inside.filter(f=>where(f,live)==='desk').length, nBed=inside.filter(f=>where(f,live)==='bed').length,
        nLounge=inside.filter(f=>where(f,live)==='lounge').length, nPanic=inside.filter(f=>where(f,live)==='panic').length;
  return `<div class="tower-in" style="--c:${T.c};--g:${T.g}">
    <div class="tin-top"><button class="btn" data-go="city">← City</button>
      <div class="tin-name px">${m.icon} ${T.name}</div>
      <div>${live?'<span class="pill live"><i></i>LIVE</span>':'<span class="pill closed">CLOSED · opens '+esc(m.next_open)+'</span>'}</div>
      <button class="btn" data-go="details">📋 Details & charts</button></div>
    ${countdown()}
    <div class="census">💹 ${nDesk} trading · ☕ ${nLounge} waiting · 💦 ${nPanic} in the KO zone · 🛏 ${nBed} asleep · 🚪 ${arriving.length} arriving · ☠ ${graves.length} in the cemetery</div>
    <div class="tin-grid"><div class="building2">
      <div class="roof2"><span class="px">${T.name}</span></div>
      ${L?apartment([L], 'P', live, m.leader, true):`<div class="apt pent empty2"><div class="fnum2 px">👑</div><div class="mu" style="padding:16px">The penthouse is empty. ${m.crown_needs_qual?'A qualified fighter in profit moves in here.':'The first fighter in profit moves in here.'}</div></div>`}
      ${groups.map((g,i)=>apartment(g, groups.length-i, live, m.leader, false)).join('')}
      <div class="lobby2"><div class="statue"><div class="ped">🗿</div><div><b>THE BOSS</b> · ${esc(a.boss.name)}<br><span class="${cls(a.boss.pnl)}">${money(a.boss.pnl)}</span> <span class="mu">(today ${money(a.boss.today)})</span></div></div>
        <div class="cage"><div class="ped">🐒</div><div><b>MONKEY CAGE</b> · ${a.monkeys?a.monkeys.n:0} random traders<br><span class="mu">typical</span> <span class="${cls((a.monkeys||{}).median)}">${money((a.monkeys||{}).median)}</span> · <span class="mu">top 25%</span> <span class="${cls((a.monkeys||{}).p75)}">${money((a.monkeys||{}).p75)}</span></div></div>
        ${propDesk(a)}
        <div class="elev"><span class="px" style="font-size:8px">🛗 ARRIVALS</span><div class="arr">${arriving.map(f=>`<div class="sp stand" data-n="${esc(f.name)}" style="position:relative;left:auto">${guy(f,'')}<i class="legs"><i></i><i></i></i><div class="tag2">${esc(f.name.slice(0,14))}</div></div>`).join('')||'<span class="mu" style="font-size:11px">nobody today</span>'}</div></div>
        <div class="mu" style="font-size:11.5px">${a.prop?`Blown accounts leave at the bell (<b style="color:#ff4d5e">${esc(m.ko_time)}</b>) · their seats go to new challengers`:`Knockouts: <b style="color:#ff4d5e">${esc(m.ko_time)}</b> · bottom ${m.ko_per_day} go to the cemetery`}</div></div>
      <div class="basement"><div class="ph-t px">🚇 THE TUNNEL · challengers waiting for a seat</div>
        <div class="bench">${a.queue.slice(0,10).map(q=>`<div class="waiter q" title="${esc(q.about)}">${guy({name:q.name,cls:q.cls},'idle')}<small>${esc(q.name)}</small><em>${q.qual.ok?'★ qualified':'on the bench'}</em></div>`).join('')}</div></div>
    </div>
    <div class="side">
      <div class="box"><h4 class="px">⚔ WHAT'S HAPPENING</h4><div class="feed" style="max-height:420px">${feedHTML(a.feed.slice(0,40))}</div></div>
      <div class="box" style="margin-top:12px"><h4 class="px">☠ CEMETERY</h4><div class="stones">${graves.map(f=>`<div class="stone" data-n="${esc(f.name)}" title="${money(f.pnl)}"><span>RIP</span><small>${esc(f.name.split(' ')[0])}</small></div>`).join('')||'<span class="mu">Nobody yet.</span>'}</div></div>
    </div></div></div>`;
}
setInterval(()=>{
  document.querySelectorAll('#arena .sp.wander').forEach(sp=>{
    if(Math.random()<0.45) return;
    const [lo,hi]=(sp.dataset.range||'0,0').split(',').map(Number); if(hi<=lo) return;
    const cur=parseFloat(sp.style.left)||lo; let nx=lo+Math.random()*(hi-lo);
    if(Math.abs(nx-cur)<3) nx = cur>(lo+hi)/2 ? lo+Math.random()*3 : hi-Math.random()*3;
    sp.classList.toggle('flip', nx<cur); sp.classList.add('walking'); sp.style.left=nx.toFixed(1)+'%';
    clearTimeout(sp._t); sp._t=setTimeout(()=>sp.classList.remove('walking'), (parseFloat(sp.dataset.dur)||2.4)*1000);
  });
}, 1700);
setInterval(tickCountdown, 1000);

function stale(){
  if(!D.built_at || !D.reload) return '';
  const mins=Math.round((Date.now()-Date.parse(D.built_at))/60000);
  if(mins<50) return '';
  const t = mins<120 ? mins+' minutes' : Math.round(mins/60)+' hours';
  return `<div class="stale">⚠ Last update was ${t} ago. GitHub is running late; this page refreshes itself as soon as the next update lands.</div>`;
}
function render(){
  pick();
  if(st.view==='city' || st.view==='tower'){
    R.innerHTML = stale() + (st.view==='city'?cityView():towerView()) + `<div class="modal"><div class="mc"><span class="x-btn">✕ close</span><div id="mbody"></div></div></div>`;
    tickCountdown();
    return;
  }
  const tabs=[['arena','ARENA'],['board','STANDINGS'],['grave','GRAVEYARD'],['queue','CHALLENGERS'],['trophy','TROPHIES']];
  if(A.reddit!==undefined || A.headlines!==undefined) tabs.push(['chatter', A.reddit===undefined?'WORLD NEWS':'CHATTER']);
  tabs.push(['rules','RULES']);
  if(!tabs.find(t=>t[0]===st.tab)) st.tab='arena';
  R.innerHTML = stale() + `
  <div class="top"><div><button class="btn" data-go="city" style="margin-bottom:8px">← City</button> <button class="btn" data-go="tower" style="margin-bottom:8px">🏢 Inside the tower</button><div class="logo px">STRATEGY ARENA</div>
    <div class="sub">${M.icon} ${esc(M.title)} · 15-min bars · last complete bar ${esc(M.last_bar)} UK · updated ${esc(M.updated)}</div></div>
    <div style="display:flex;gap:14px;align-items:center;max-width:60%">
      ${M.live?'<span class="pill live"><i></i>LIVE</span>':'<span class="pill closed">MARKET CLOSED</span>'}${ticker()}</div></div>
  ${switcher()}
  ${hero()}
  <div class="tabs">${tabs.map(([k,l])=>`<div class="tab px ${st.tab===k?'on':''}" data-tab="${k}">${l}</div>`).join('')}</div>
  <div id="view">${view()}</div>
  <div class="modal"><div class="mc"><span class="x-btn">✕ close</span><div id="mbody"></div></div></div>`;
}
R.addEventListener('click', e=>{
  const tw=e.target.closest('[data-tower]'); if(tw){st.arena=tw.dataset.tower; st.view='tower'; save(); render(); R.scrollIntoView({block:'start'}); return;}
  const go=e.target.closest('[data-go]'); if(go){st.view=go.dataset.go; save(); render(); return;}
  const ar=e.target.closest('[data-arena]'); if(ar){st.arena=ar.dataset.arena; save(); render(); return;}
  const t=e.target.closest('[data-tab]'); if(t){st.tab=t.dataset.tab; save(); render(); return;}
  const so=e.target.closest('[data-sort]'); if(so){st.sort=so.dataset.sort; save(); render(); return;}
  const fi=e.target.closest('[data-filter]'); if(fi){st.filter=fi.dataset.filter; save(); render(); return;}
  const ab=e.target.closest('[data-asset]'); if(ab){openModal(modalName, ab.dataset.asset); return;}
  if(e.target.closest('.x-btn') || e.target.classList.contains('modal')){R.querySelector('.modal').classList.remove('on'); return;}
  const c=e.target.closest('[data-n]'); if(c){ if(c.dataset.k){st.arena=c.dataset.k; pick();} openModal(c.dataset.n);}
});
render();
if(D.reload){ setTimeout(()=>{ try{ if(!R.querySelector('.modal.on')) location.reload(); else setTimeout(()=>location.reload(), 60000);}catch(e){} }, D.reload*1000); }
})();
</script>
"""


def render(states, order, reload_sec=None, final_at=None, frozen=None, built_at=None):
    data = json.dumps(dict(arenas=states, order=order, reload=reload_sec, final_at=final_at, frozen=frozen, built_at=built_at),
                      default=str).replace("</", "<\\/")
    return CSS + '<div id="arena"></div>' + JS.replace("__DATA__", data)
