/*!
 * 空間疫学入門 - storage.js
 *
 * localStorageへの章末クイズ合格状態の保存・読み出しを担う共通モジュール。
 * window.SPEPI として他のスクリプト(quiz.js / progress.js)から利用される。
 *
 * 移植元: https://github.com/youkiti/ai-kotohajime の storage.js(window.AIK)。
 * 本教材は日本語のみのため、移植元にあったi18n(言語判定・英語文字列)は
 * 持ち込まず、日本語文字列を直接埋め込む。実践課題(exercise)関連の
 * キー・APIも移植しない(exercise.jsを移植しないため)。
 *
 * 設計方針:
 * - サーバへは一切送信しない。保存先はこの端末のlocalStorageのみ。
 *   保存するのは合格日時のみ。
 * - localStorageが使えない環境(プライベートブラウズ等)でも例外で
 *   ページ全体が壊れないよう、すべての読み書きをtry/catchで保護する。
 *   その場合は保存が効かないだけで、機能自体はそのセッション内で動作継続する
 *   (メモリ上のフォールバックストアを使用)。
 * - ES5〜ES2017程度の範囲で記述し、ビルド工程なしでそのまま配信する。
 */
(function () {
  "use strict";

  var QUIZ_PREFIX = "spatialepi.quiz.";

  // localStorageが使えない場合のフォールバック(このタブ・セッション限り)
  var memoryStore = {};
  var memoryFallbackActive = false;

  function storageGet(key) {
    if (!memoryFallbackActive) {
      try {
        return window.localStorage.getItem(key);
      } catch (e) {
        memoryFallbackActive = true;
      }
    }
    return Object.prototype.hasOwnProperty.call(memoryStore, key) ? memoryStore[key] : null;
  }

  function storageSet(key, value) {
    if (!memoryFallbackActive) {
      try {
        window.localStorage.setItem(key, value);
        return;
      } catch (e) {
        memoryFallbackActive = true;
      }
    }
    memoryStore[key] = value;
  }

  // 概念パート6章の定義(章キー: 表示名)。クイズ読み込み失敗時のエラー文言や
  // 進捗表示のラベル組み立てに使う(カリキュラム設計.md §2 の章見出しに準拠)。
  var CHAPTERS = {
    ch1: "章1 記述 — どこで多い?",
    ch2: "章2 空間重み行列 — 「隣」を先に決める",
    ch3: "章3 Global Moran's I — 全体として偏っている?",
    ch4: "章4 LISA / Gi* / SaTScan の違い",
    ch5: "章5 説明 — なぜそこに多い?",
    ch6: "章6 初学者が注意する5つの落とし穴"
  };
  var CHAPTER_KEYS = ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6"];

  function passedKey(chapter) {
    return QUIZ_PREFIX + chapter + ".passedAt";
  }

  function nowIso() {
    var iso;
    try {
      iso = new Date().toISOString();
    } catch (e) {
      iso = "" + new Date().getTime();
    }
    return iso;
  }

  // 指定章の章末クイズ合格日時(ISO 8601文字列)。未合格ならnull。
  function passedAt(chapter) {
    if (!Object.prototype.hasOwnProperty.call(CHAPTERS, chapter)) {
      return null;
    }
    var v = storageGet(passedKey(chapter));
    return v ? v : null;
  }

  // 指定章の章末クイズに合格済みか
  function isPassed(chapter) {
    return !!passedAt(chapter);
  }

  // 指定章の章末クイズを合格済みとして記録する。既に合格済みの場合は日時を上書きしない。
  function setPassed(chapter) {
    if (!Object.prototype.hasOwnProperty.call(CHAPTERS, chapter)) {
      return;
    }
    if (passedAt(chapter)) {
      return;
    }
    storageSet(passedKey(chapter), nowIso());
  }

  // ISO 8601文字列 -> 「2026年7月13日」形式。不正な値の場合は空文字を返す。
  function formatDate(iso) {
    if (!iso) {
      return "";
    }
    var d = new Date(iso);
    if (isNaN(d.getTime())) {
      return "";
    }
    return d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日";
  }

  // JSON等の外部データ由来の文字列をHTMLとして安全に挿入するためのエスケープ関数。
  // quiz.js / progress.js から呼び出される想定(本ファイル自身は主にDOM APIで
  // 描画するため未使用箇所もある)。
  function escapeHtml(str) {
    if (str === null || str === undefined) {
      return "";
    }
    return String(str).replace(/[&<>"']/g, function (ch) {
      switch (ch) {
        case "&":
          return "&amp;";
        case "<":
          return "&lt;";
        case ">":
          return "&gt;";
        case '"':
          return "&quot;";
        case "'":
          return "&#39;";
        default:
          return ch;
      }
    });
  }

  // 章キー(ch1〜ch6)から表示ラベルを組み立てる(quiz.js・progress.jsで共用)。
  // 未知のキーの場合は、そのままchapterを返す。
  function chapterLabel(chapter) {
    if (!Object.prototype.hasOwnProperty.call(CHAPTERS, chapter)) {
      return chapter;
    }
    return CHAPTERS[chapter];
  }

  window.SPEPI = {
    CHAPTERS: CHAPTERS,
    CHAPTER_KEYS: CHAPTER_KEYS,
    passedAt: passedAt,
    isPassed: isPassed,
    setPassed: setPassed,
    formatDate: formatDate,
    escapeHtml: escapeHtml,
    chapterLabel: chapterLabel
  };
})();
