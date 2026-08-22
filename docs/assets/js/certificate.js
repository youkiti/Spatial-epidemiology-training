/*!
 * 空間疫学入門 - certificate.js
 *
 * `[data-certificate]` を持つ要素に修了証発行UIを描画する。
 * 概念パート全6章(ch1〜ch6)の章末クイズにすべて合格するまではロック表示のみとし、
 * 合格後に氏名入力 -> Canvas描画 -> PNGプレビュー/ダウンロード/共有のUIを出す。
 *
 * ページ側の契約:
 *   <div data-certificate data-cert-locked="〜すると発行できます。"></div>
 *   data-cert-locked は省略可(既定文言を使う)。
 *
 * サーバへは一切送信しない。氏名はCanvas描画にのみ使用し、localStorageにも
 * 保存せず、Xポスト用リンクにも含めない(意図的な設計判断。ai-kotohajime の
 * certificate.js の設計をそのまま踏襲する)。fetch/XMLHttpRequest/<form>/
 * submitのいずれも本ファイルは持たない。
 *
 * 移植元: https://github.com/youkiti/ai-kotohajime の certificate.js。
 * 移植元は「領域(area) A/B/C + 初級」の4種類・日英2言語・実践課題(exercise)ありの
 * 構成だったが、本教材にはそのどれも無いため単純なコピーではなく書き直した。
 * - i18n(言語判定・英語フォントスタック・英語文字列テーブル)は持ち込まない。
 *   本教材は日本語のみのため(storage.js / progress.js と同じ判断)。
 * - 発行単位は「概念パート全6章の章末クイズにすべて合格したら1枚」の1種類のみ。
 *   data-cert-area="a"|"b"|"c"|"shokyu" のような分岐は無く、
 *   areaDisplayName / areaLabel / requiresExercise / fileSafeSuffix 相当も無い。
 * - 記録消去ボタン(移植元 mokuroku.md の data-reset-progress)は移植しない
 *   (ユーザー確認済みの決定。storage.jsに消去APIも足していない)。
 */
(function () {
  "use strict";

  // storage.js (読み込み順で先行)がwindow.SPEPIを定義する。ここで一度だけ束縛し、
  // 以後はこのローカル変数のみを参照する(bareなグローバル参照に依存しない)。
  var SPEPI = window.SPEPI || null;

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  // Canvas描画用フォントスタック。Windows/macOS/Linuxのいずれでも和文が
  // 豆腐(表示不可文字の四角)にならないよう、各OS標準の明朝体を並べ、
  // 最後は総称serifで締める(移植元のFONT_STACK_JAにLinux向けを追加)。
  var FONT_STACK =
    '"Yu Mincho","YuMincho","Hiragino Mincho ProN","Noto Serif JP","Noto Serif CJK JP","IPAexMincho","MS PMincho",serif';

  var COLOR_BG = "#f8f3e7";
  var COLOR_FRAME = "#4a3f2f";
  var COLOR_TEXT = "#2b2116";
  var COLOR_MUTED = "#7a6f5d";
  var COLOR_SEAL = "#b7282e";

  var DOWNLOAD_FILE_NAME = "spatial-epidemiology-certificate.png";

  // UI文字列(発行フォーム・共有ボタン・Canvas上の定型文言)。i18nテーブルは
  // 持ち込まず、日本語文字列を直接埋め込む。
  var T = {
    footerIssued: function (today) {
      return "発行日: " + today;
    },
    footerSite: "空間疫学入門 ― 疫学の素養がある読者のための空間疫学教材 ―",
    disclaimer: "本修了証は自己学習の記録として本人が発行したものであり、公式な修了の証明ではありません。",
    tweetText: "「空間疫学入門」の修了証を発行しました! #空間疫学入門",
    downloadBtn: "PNGをダウンロード",
    xBtn: "Xでポストする",
    xHint: "文面のみ入力されます。ダウンロードした画像を投稿に添付してください。スマホでは共有から画像ごとシェアできます。",
    shareBtn: "共有(スマホ等)",
    nameLabel: "お名前(ニックネーム可)",
    namePlaceholder: "例: 山田 太郎 / やまだ",
    nameHint: "SNSで実名を出したくない場合はニックネームで発行できます。入力した名前はこの端末の外に送信されません。",
    issueBtn: "修了証を発行する",
    nameRequired: "お名前(ニックネーム可)を入力してください。",
    lockedDefault: "全6章の章末クイズにすべて合格すると発行できます。",
    remainingPrefix: "未合格: ",
    remainingSep: " / ",
    genError: "修了証の生成に失敗しました。ブラウザの設定をご確認のうえ、再度お試しください。",
    imgError: "画像の生成に失敗しました。",
    altText: "修了証のプレビュー画像",
    title: "修了証",
    subtitle: "概念パート 全6章修了",
    body: "上記の者は、空間疫学入門における概念パート全6章の章末クイズにすべて合格したことをここに記す。",
    sealChar1: "空",
    sealChar2: "間"
  };

  // 未合格の章キー(ch1〜ch6のうち)を、表示順のまま返す。
  // 判定はSPEPI.CHAPTER_KEYSとSPEPI.isPassed()のみで行い、localStorageの
  // キーを直接読まない(storage.jsの公開APIに一本化する)。
  function unpassedChapters() {
    var result = [];
    if (!SPEPI) {
      return result;
    }
    var keys = SPEPI.CHAPTER_KEYS;
    for (var i = 0; i < keys.length; i++) {
      if (!SPEPI.isPassed(keys[i])) {
        result.push(keys[i]);
      }
    }
    return result;
  }

  function allPassed() {
    return !!SPEPI && unpassedChapters().length === 0;
  }

  // 1章でも合格していれば真(progress.jsのhasAnyProgress()と同じ判定を、
  // storage.jsの公開APIのみで行う)。
  function hasAnyProgress() {
    if (!SPEPI) {
      return false;
    }
    var keys = SPEPI.CHAPTER_KEYS;
    for (var i = 0; i < keys.length; i++) {
      if (SPEPI.isPassed(keys[i])) {
        return true;
      }
    }
    return false;
  }

  // ロック中に「残っている章」を読者にわかる1行にする(例: "未合格: 章3 / 章5")。
  // 1章も合格していない初回訪問時は出さない: ロック文言が既に「全6章合格が必要」と
  // 言っているため、この時点で全章を列挙しても同じ情報の繰り返しにしかならない
  // (progress.jsが「進捗が一つも無い場合は初回訪問時の情報量を増やさない」方針を
  // 明記しているのと同じ考え方)。全章合格済み、またはSPEPIが無い場合も空文字を返す。
  function remainingLine() {
    if (!hasAnyProgress()) {
      return "";
    }
    var chapters = unpassedChapters();
    if (chapters.length === 0) {
      return "";
    }
    var labels = [];
    for (var i = 0; i < chapters.length; i++) {
      labels.push("章" + chapters[i].replace(/^ch/, ""));
    }
    return T.remainingPrefix + labels.join(T.remainingSep);
  }

  // 表題「修　了　証」。全角空白で字間を空ける(移植元のspacedTitleと同じ作り方)。
  function spacedTitle() {
    return T.title.split("").join("　");
  }

  // 文字単位で折り返して行配列を作る(日本語の単語区切りに依存しない簡易実装)
  function wrapTextByChar(ctx, text, maxWidth) {
    var lines = [];
    var current = "";
    for (var i = 0; i < text.length; i++) {
      var testLine = current + text.charAt(i);
      if (current !== "" && ctx.measureText(testLine).width > maxWidth) {
        lines.push(current);
        current = text.charAt(i);
      } else {
        current = testLine;
      }
    }
    if (current !== "") {
      lines.push(current);
    }
    return lines;
  }

  // 指定の最大幅に収まるまでフォントサイズを縮小する(長い氏名対策)
  function fitFontSize(ctx, text, maxWidth, baseSize, minSize) {
    var size = baseSize;
    ctx.font = "bold " + size + "px " + FONT_STACK;
    while (size > minSize && ctx.measureText(text).width > maxWidth) {
      size -= 2;
      ctx.font = "bold " + size + "px " + FONT_STACK;
    }
    return size;
  }

  function drawCertificate(name) {
    var canvas = document.createElement("canvas");
    canvas.width = 1600;
    canvas.height = 1000;
    var ctx = canvas.getContext("2d");

    // 背景(生成りの地)
    ctx.fillStyle = COLOR_BG;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 二重枠: 太い外枠
    ctx.strokeStyle = COLOR_FRAME;
    ctx.lineWidth = 18;
    ctx.strokeRect(30, 30, canvas.width - 60, canvas.height - 60);

    // 二重枠: 細い内枠
    ctx.lineWidth = 4;
    ctx.strokeRect(64, 64, canvas.width - 128, canvas.height - 128);

    // 表題「修　了　証」
    ctx.textAlign = "center";
    ctx.fillStyle = COLOR_TEXT;
    ctx.font = "bold 108px " + FONT_STACK;
    ctx.fillText(spacedTitle(), 800, 230);

    // 副題「概念パート 全6章修了」
    ctx.font = "42px " + FONT_STACK;
    ctx.fillText(T.subtitle, 800, 320);

    // 氏名「〜　殿」。長い氏名でも枠内に収まるよう自動縮小
    var nameText = (name || "") + "　殿";
    var nameFontSize = fitFontSize(ctx, nameText, 1350, 68, 30);
    ctx.font = "bold " + nameFontSize + "px " + FONT_STACK;
    ctx.fillStyle = COLOR_TEXT;
    ctx.fillText(nameText, 800, 450);

    // 本文(文字単位で折り返し)
    ctx.font = "32px " + FONT_STACK;
    ctx.fillStyle = COLOR_TEXT;
    var bodyLines = wrapTextByChar(ctx, T.body, 1150);
    var bodyStartY = 560;
    var bodyLineHeight = 52;
    for (var i = 0; i < bodyLines.length; i++) {
      ctx.fillText(bodyLines[i], 800, bodyStartY + i * bodyLineHeight);
    }

    // フッター(発行日・サイト名): 左寄せにして落款(右下)と重ならないようにする
    ctx.textAlign = "left";
    ctx.fillStyle = COLOR_TEXT;
    ctx.font = "26px " + FONT_STACK;
    // SPEPIにtodayString()相当は無いため、formatDate(現在時刻のISO文字列)で組み立てる。
    // SPEPIが無い場合は空文字にフォールバックする。
    ctx.fillText(T.footerIssued(SPEPI ? SPEPI.formatDate(new Date().toISOString()) : ""), 140, 750);
    ctx.fillText(T.footerSite, 140, 800);

    // 免責文言(小さく・グレー)
    ctx.font = "18px " + FONT_STACK;
    ctx.fillStyle = COLOR_MUTED;
    var disclaimerLines = wrapTextByChar(ctx, T.disclaimer, 1100);
    for (var d = 0; d < disclaimerLines.length; d++) {
      ctx.fillText(disclaimerLines[d], 140, 850 + d * 26);
    }

    // 落款(右下、朱色の正方形に白抜き文字)。移植元の「事」「始」に代えて「空」「間」。
    var sealX = 1310;
    var sealY = 740;
    var sealSize = 150;
    ctx.fillStyle = COLOR_SEAL;
    ctx.fillRect(sealX, sealY, sealSize, sealSize);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 3;
    ctx.strokeRect(sealX + 10, sealY + 10, sealSize - 20, sealSize - 20);

    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.font = "bold 56px " + FONT_STACK;
    ctx.fillText(T.sealChar1, sealX + sealSize / 2, sealY + sealSize / 2 - 8);
    ctx.fillText(T.sealChar2, sealX + sealSize / 2, sealY + sealSize / 2 + 62);

    return canvas;
  }

  function issueCertificate(name, resultWrap) {
    resultWrap.innerHTML = "";
    resultWrap.removeAttribute("hidden");

    var canvas;
    try {
      canvas = drawCertificate(name);
    } catch (e) {
      var errP = document.createElement("p");
      errP.className = "spepi-cert-error";
      errP.textContent = T.genError;
      resultWrap.appendChild(errP);
      return;
    }

    var dataUrl;
    try {
      dataUrl = canvas.toDataURL("image/png");
    } catch (e) {
      var errP2 = document.createElement("p");
      errP2.className = "spepi-cert-error";
      errP2.textContent = T.imgError;
      resultWrap.appendChild(errP2);
      return;
    }

    var img = document.createElement("img");
    img.className = "spepi-cert-preview";
    img.src = dataUrl;
    img.alt = T.altText;
    resultWrap.appendChild(img);

    var actions = document.createElement("div");
    actions.className = "spepi-cert-actions";
    resultWrap.appendChild(actions);

    var downloadLink = document.createElement("a");
    downloadLink.className = "md-button";
    downloadLink.href = dataUrl;
    downloadLink.setAttribute("download", DOWNLOAD_FILE_NAME);
    downloadLink.textContent = T.downloadBtn;
    actions.appendChild(downloadLink);

    // Xポストは文面のみで、氏名は含めない(意図的な設計判断。ヘッダー参照)。
    var tweetLink = document.createElement("a");
    tweetLink.className = "md-button";
    tweetLink.href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(T.tweetText);
    tweetLink.target = "_blank";
    tweetLink.rel = "noopener noreferrer";
    tweetLink.textContent = T.xBtn;
    actions.appendChild(tweetLink);

    var tweetHint = document.createElement("p");
    tweetHint.className = "spepi-cert-hint";
    tweetHint.textContent = T.xHint;
    resultWrap.appendChild(tweetHint);

    // Web Share API (Level 2: ファイル共有) - 対応環境でのみ「共有」ボタンを追加する。
    // toBlob/File/navigator.canShareの三重の存在チェックを経て初めてボタンを出す。
    if (typeof canvas.toBlob === "function") {
      try {
        canvas.toBlob(function (blob) {
          if (!blob) {
            return;
          }
          try {
            var file = new File([blob], DOWNLOAD_FILE_NAME, {
              type: "image/png"
            });
            if (navigator.canShare && navigator.canShare({ files: [file] })) {
              var shareBtn = document.createElement("button");
              shareBtn.type = "button";
              shareBtn.className = "md-button";
              shareBtn.textContent = T.shareBtn;
              shareBtn.addEventListener("click", function () {
                navigator
                  .share({
                    files: [file],
                    text: T.tweetText
                  })
                  .catch(function () {
                    // ユーザーによるキャンセル等。エラー表示はせず静かに戻る。
                  });
              });
              actions.insertBefore(shareBtn, tweetLink);
            }
          } catch (e) {
            // File API 非対応、またはcanShare判定に失敗。共有ボタンなしで続行。
          }
        }, "image/png");
      } catch (e) {
        // toBlob非対応環境。ダウンロード/Xポストのみ提供する。
      }
    }
  }

  function buildIssueUI(container) {
    var wrap = document.createElement("div");
    wrap.className = "spepi-cert-issue";

    var label = document.createElement("label");
    label.className = "spepi-cert-name-label";
    label.textContent = T.nameLabel;

    var nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.className = "spepi-cert-name-input";
    nameInput.placeholder = T.namePlaceholder;
    nameInput.setAttribute("maxlength", "30");

    label.appendChild(document.createElement("br"));
    label.appendChild(nameInput);
    wrap.appendChild(label);

    var hint = document.createElement("p");
    hint.className = "spepi-cert-hint";
    hint.textContent = T.nameHint;
    wrap.appendChild(hint);

    var errorMsg = document.createElement("p");
    errorMsg.className = "spepi-cert-error";
    errorMsg.setAttribute("hidden", "hidden");
    wrap.appendChild(errorMsg);

    var issueBtn = document.createElement("button");
    issueBtn.type = "button";
    issueBtn.className = "md-button md-button--primary";
    issueBtn.textContent = T.issueBtn;
    wrap.appendChild(issueBtn);

    var resultWrap = document.createElement("div");
    resultWrap.className = "spepi-cert-result";
    resultWrap.setAttribute("hidden", "hidden");
    wrap.appendChild(resultWrap);

    issueBtn.addEventListener("click", function () {
      var name = nameInput.value.replace(/^\s+|\s+$/g, "");
      if (!name) {
        errorMsg.textContent = T.nameRequired;
        errorMsg.removeAttribute("hidden");
        nameInput.focus();
        return;
      }
      errorMsg.setAttribute("hidden", "hidden");
      issueCertificate(name, resultWrap);
    });

    container.appendChild(wrap);
  }

  function renderCertBlock(container) {
    var lockedText = container.getAttribute("data-cert-locked") || T.lockedDefault;

    var passed = allPassed();

    // 解錠済みUIが構築済みなら作り直さない(再合格イベントで入力済みの
    // 氏名や発行済みプレビューを消してしまわないため)。
    if (passed && container.getAttribute("data-cert-state") === "unlocked") {
      return;
    }
    container.setAttribute("data-cert-state", passed ? "unlocked" : "locked");

    container.innerHTML = "";

    if (!passed) {
      var lockedP = document.createElement("p");
      lockedP.className = "spepi-cert-locked";
      lockedP.textContent = "🔒 " + lockedText;
      container.appendChild(lockedP);

      var remaining = remainingLine();
      if (remaining) {
        var remainingP = document.createElement("p");
        remainingP.className = "spepi-cert-remaining";
        remainingP.textContent = remaining;
        container.appendChild(remainingP);
      }
      return;
    }

    buildIssueUI(container);
  }

  function renderAll() {
    var containers = document.querySelectorAll("[data-certificate]");
    for (var i = 0; i < containers.length; i++) {
      renderCertBlock(containers[i]);
    }
  }

  ready(renderAll);

  // 章末クイズ合格イベントで再描画する。発行条件が「全6章合格」の1種類だけなので、
  // 移植元のような「関係するブロックだけ再描画」の絞り込みは不要で、
  // どの章の合格イベントでも無条件に全ブロックを再判定する。
  document.addEventListener("spepi:passed", renderAll);
})();
