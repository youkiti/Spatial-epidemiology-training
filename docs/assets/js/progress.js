/*!
 * 空間疫学入門 - progress.js
 *
 * `[data-chapter-progress]` を持つ要素に、章ページ上部向けの
 * 軽量な進捗表示(1行)を描画する。
 *
 * 表示方針:
 * - 全6章のいずれにも進捗(章末クイズ合格)が一切ない場合は何も描画しない
 *   (初回訪問時の情報量を増やさない)
 * - 一つでも進捗があれば、各章の状態(✓修了/未)を1行で表示する。
 *
 * ページ側の契約:
 *   <div data-chapter-progress></div>
 *
 * window.SPEPI(storage.js)に依存する。読み込み順は mkdocs.yml で
 * storage.js -> quiz.js -> progress.js に固定。
 * localStorageへの書き込み・サーバ送信は一切行わない(読み取りと描画のみ)。
 *
 * 移植元: https://github.com/youkiti/ai-kotohajime の progress.js。
 * 移植元は「領域(area)」単位だったが、本教材は「章(chapter)」単位のため、
 * データ属性を data-area-progress から data-chapter-progress に改名し、
 * 章キーを ch1〜ch6 に差し替えた。実践課題(exercise)を移植しないため、
 * 移植元にあった「途中(partial)」状態(クイズ合格・課題提出の片方のみ)は無く、
 * 状態は「修了」「未」の2値になる。i18nも本教材は日本語のみのため持ち込まない。
 */
(function () {
  "use strict";

  // storage.js (読み込み順で先行)がwindow.SPEPIを定義する。ここで一度だけ束縛し、
  // 以後はこのローカル変数のみを参照する(bareなグローバル参照に依存しない)。
  var SPEPI = window.SPEPI || null;

  // UI文字列(進捗行の文言)
  var T = {
    prefix: "学習の進捗: ",
    passed: function (n) {
      return "章" + n + " ✓修了";
    },
    none: function (n) {
      return "章" + n + " 未";
    },
    chapterSep: " / "
  };

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  // 章キー(ch1〜ch6)から表示用の章番号("1"〜"6")を取り出す。
  function chapterNumber(chapter) {
    return chapter.replace(/^ch/, "");
  }

  // 章の状態を返す: "passed"(修了) | "none"(未着手)。
  // 判定はすべてstorage.jsの公開APIのみで行う(進捗キーの直接参照はしない)。
  function chapterState(chapter) {
    if (!SPEPI) {
      return "none";
    }
    return SPEPI.isPassed(chapter) ? "passed" : "none";
  }

  function hasAnyProgress() {
    var keys = SPEPI ? SPEPI.CHAPTER_KEYS : [];
    for (var i = 0; i < keys.length; i++) {
      if (chapterState(keys[i]) !== "none") {
        return true;
      }
    }
    return false;
  }

  function renderProgress(container) {
    container.innerHTML = "";

    // 進捗が一つもない場合は何も描画しない(初回訪問時の情報量を増やさない)
    if (!SPEPI || !hasAnyProgress()) {
      return;
    }

    var p = document.createElement("p");
    p.className = "spepi-chapter-progress";

    var prefixSpan = document.createElement("span");
    prefixSpan.className = "spepi-chapter-progress-prefix";
    prefixSpan.textContent = T.prefix;
    p.appendChild(prefixSpan);

    var keys = SPEPI.CHAPTER_KEYS;
    for (var i = 0; i < keys.length; i++) {
      var chapter = keys[i];
      if (i > 0) {
        p.appendChild(document.createTextNode(T.chapterSep));
      }
      var state = chapterState(chapter);
      var num = chapterNumber(chapter);
      var span = document.createElement("span");
      span.className = state === "passed" ? "spepi-status-passed" : "spepi-status-unpassed";
      span.textContent = state === "passed" ? T.passed(num) : T.none(num);
      p.appendChild(span);
    }

    container.appendChild(p);
  }

  function renderAll() {
    var containers = document.querySelectorAll("[data-chapter-progress]");
    for (var i = 0; i < containers.length; i++) {
      renderProgress(containers[i]);
    }
  }

  ready(renderAll);

  // 章末クイズ合格が同一ページ内で起きた直後にも反映されるよう、
  // 状態変化イベントで再描画する。
  document.addEventListener("spepi:passed", renderAll);
})();
