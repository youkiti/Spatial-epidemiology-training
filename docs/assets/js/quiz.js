/*!
 * 空間疫学入門 - quiz.js
 *
 * `[data-quiz-src]` を持つ要素にクイズJSONを読み込んで描画し、一括採点する。
 *
 * ページ側の契約:
 *   <div data-quiz-src="../../assets/data/quiz-ch1.json" data-quiz-gate="ch1"></div>
 *   - data-quiz-gate が無い場合は自己チェック(合否表示はするが合格保存はしない)
 *   - data-quiz-gate がある場合は章末クイズ(合格をlocalStorageに保存する)
 *
 * 実装方針:
 * - 外部ライブラリなし。fetchはサイト内JSONのみ。
 * - 描画はDOM API(createElement/textContent)で行い、JSON由来の文字列が
 *   HTMLとして解釈されないようにする(= HTMLエスケープ要件を満たす)。
 * - window.SPEPI(storage.js)に依存する。読み込み順は mkdocs.yml で
 *   storage.js -> quiz.js -> progress.js に固定されている。
 *
 * 移植元: https://github.com/youkiti/ai-kotohajime の quiz.js。
 * 本教材は日本語のみのため、移植元にあったi18nは持ち込まず、日本語文字列を
 * 直接埋め込む。実践課題(exercise)・証明書(certificate)関連のコードは
 * 移植しない。
 */
(function () {
  "use strict";

  // storage.js (読み込み順で先行)がwindow.SPEPIを定義する。ここで一度だけ束縛し、
  // 以後はこのローカル変数のみを参照する(bareなグローバル参照に依存しない)。
  var SPEPI = window.SPEPI || null;

  // UI文字列(採点結果・注記・エラー等)
  var T = {
    qNum: function (n) {
      return "問" + n;
    },
    listSep: "、",
    submitBtn: "採点する",
    clearBtn: "選択をクリア",
    unansweredWarningPrefix: "⚠ 未回答の問題があります: ",
    incorrectListPrefix: "不正解: ",
    correct: "✅ 正解",
    incorrect: function (correctText) {
      return "❌ 不正解(正解: " + correctText + ")";
    },
    explanation: function (text) {
      return "解説: " + text;
    },
    scoreWithGate: function (correct, total, passLine) {
      return "正答数: " + correct + " / " + total + "問(合格ライン: " + passLine + "問以上)";
    },
    scoreNoGate: function (correct, total) {
      return "正答数: " + correct + " / " + total + "問";
    },
    pass: "🎉 合格です!",
    fail: function (needed) {
      return "合格まであと" + needed + "問。解説を読んでもう一度挑戦しましょう(回数無制限)。";
    },
    unsupportedBrowser:
      "⚠ お使いのブラウザは対応していないため、クイズを表示できません。ブラウザを最新の状態に更新してください。",
    loading: "クイズを読み込んでいます…",
    loadError: function (label) {
      return "⚠ " + label + "クイズの読み込みに失敗しました。ページを再読み込みするか、しばらく経ってから再度お試しください。";
    },
    alreadyPassedNote: function (date) {
      return "✅ この章末クイズは合格済みです(" + date + ")。再挑戦もできます。";
    }
  };

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function el(tag, opts) {
    var e = document.createElement(tag);
    if (opts) {
      if (opts.className) {
        e.className = opts.className;
      }
      if (opts.text !== undefined) {
        e.textContent = opts.text;
      }
    }
    return e;
  }

  function renderMessage(container, className, text) {
    container.innerHTML = "";
    container.appendChild(el("p", { className: className, text: text }));
  }

  var quizInstanceCounter = 0;

  // 設問idの命名規則(instanceId + "-question-" + 問番号)を一箇所に集約する。
  // radioのname(instanceId + "-q" + idx、0始まり)とは別命名にして混同を避ける。
  function questionAnchorId(instanceId, questionNumber) {
    return instanceId + "-question-" + questionNumber;
  }

  // prefix文字列 + 問番号アンカーのリストをDOM要素に組み立てる(未回答警告・不正解一覧で共用)。
  // JSON由来の文字列をinnerHTMLに入れない方針を維持するため、DOM APIのみで構築する。
  function renderQuestionListMessage(target, prefix, instanceId, nums) {
    target.textContent = "";
    target.appendChild(document.createTextNode(prefix));
    for (var i = 0; i < nums.length; i++) {
      if (i > 0) {
        target.appendChild(document.createTextNode(T.listSep));
      }
      var a = document.createElement("a");
      a.href = "#" + questionAnchorId(instanceId, nums[i]);
      a.textContent = T.qNum(nums[i]);
      target.appendChild(a);
    }
  }

  // 章キー(gate)から表示ラベルを組み立てる。SPEPI.chapterLabel()に一本化する
  // (SPEPIが無い、またはSPEPI.CHAPTERSに未知のキーの場合は既存どおりgate自体を返す)。
  function chapterLabelFor(gate) {
    if (!SPEPI || !SPEPI.CHAPTERS || !SPEPI.CHAPTERS[gate]) {
      return gate;
    }
    return SPEPI.chapterLabel(gate);
  }

  function buildQuiz(container, data, gate) {
    var instanceId = "spepiquiz" + quizInstanceCounter++;
    var questions = data.questions;
    var passRatio = typeof data.passRatio === "number" && data.passRatio > 0 ? data.passRatio : 0.8;

    container.innerHTML = "";

    // 既に合格済みの章末クイズには、上部に注記を出す(クイズ自体は再挑戦可能なまま残す)。
    if (gate && SPEPI && SPEPI.passedAt(gate)) {
      var note = el("p", {
        className: "spepi-quiz-passed-note",
        text: T.alreadyPassedNote(SPEPI.formatDate(SPEPI.passedAt(gate)))
      });
      container.appendChild(note);
    }

    if (data.title) {
      var titleP = el("p", { className: "spepi-quiz-title" });
      var strong = document.createElement("strong");
      strong.textContent = data.title;
      titleP.appendChild(strong);
      container.appendChild(titleP);
    }

    var form = el("form", { className: "spepi-quiz-form" });
    form.setAttribute("novalidate", "novalidate");

    var entries = []; // { fieldset, feedback, question }

    for (var i = 0; i < questions.length; i++) {
      (function (q, idx) {
        var fieldset = el("fieldset", { className: "spepi-quiz-question" });
        // 未回答警告・不正解一覧からアンカーリンクで飛べるように一意なidを振る。
        // tabindex="-1"はスクリプトからのフォーカス移動のみを許可するため(Tabキー操作の順序には入らない)。
        fieldset.id = questionAnchorId(instanceId, idx + 1);
        fieldset.setAttribute("tabindex", "-1");
        var legend = el("legend", { text: T.qNum(idx + 1) + ". " + q.q });
        fieldset.appendChild(legend);

        var choicesWrap = el("div", { className: "spepi-quiz-choices" });
        for (var c = 0; c < q.choices.length; c++) {
          var label = el("label", { className: "spepi-quiz-choice" });
          var input = document.createElement("input");
          input.type = "radio";
          input.name = instanceId + "-q" + idx;
          input.value = String(c);
          // 選択した瞬間に未回答ハイライトを外す(採点し直さなくても視覚的に解消される)。
          input.addEventListener("change", function () {
            fieldset.classList.remove("spepi-quiz-question--unanswered");
          });
          label.appendChild(input);
          var span = el("span", { text: q.choices[c] });
          label.appendChild(span);
          choicesWrap.appendChild(label);
        }
        fieldset.appendChild(choicesWrap);

        var feedback = el("div", { className: "spepi-quiz-feedback" });
        feedback.setAttribute("hidden", "hidden");
        fieldset.appendChild(feedback);

        form.appendChild(fieldset);
        entries.push({ fieldset: fieldset, feedback: feedback, question: q, index: idx });
      })(questions[i], i);
    }

    var warning = el("p", { className: "spepi-quiz-warning" });
    warning.setAttribute("hidden", "hidden");
    form.appendChild(warning);

    var actions = el("div", { className: "spepi-quiz-actions" });

    var submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.className = "md-button md-button--primary";
    submitBtn.textContent = T.submitBtn;
    actions.appendChild(submitBtn);

    // 「選択をクリア」は非primaryの控えめなmd-buttonにして、採点ボタンより目立たせない。
    var clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "md-button";
    clearBtn.textContent = T.clearBtn;
    actions.appendChild(clearBtn);

    form.appendChild(actions);

    var summary = el("div", { className: "spepi-quiz-summary" });
    summary.setAttribute("hidden", "hidden");
    form.appendChild(summary);

    submitBtn.addEventListener("click", function () {
      gradeQuiz(instanceId, entries, form, warning, summary, passRatio, gate);
    });

    clearBtn.addEventListener("click", function () {
      resetQuiz(entries, warning, summary);
    });

    container.appendChild(form);
  }

  function gradeQuiz(instanceId, entries, form, warning, summary, passRatio, gate) {
    var unanswered = [];
    var answers = [];

    // 前回の採点で付いた未回答ハイライトを一旦すべて除去してから今回分を再判定する
    // (選択時にも個別に外しているが、ここでも取りこぼしなく揃える)。
    for (var i = 0; i < entries.length; i++) {
      entries[i].fieldset.classList.remove("spepi-quiz-question--unanswered");
    }

    for (i = 0; i < entries.length; i++) {
      var name = instanceId + "-q" + entries[i].index;
      var checked = form.querySelector('input[name="' + name + '"]:checked');
      if (checked) {
        answers.push(parseInt(checked.value, 10));
      } else {
        answers.push(null);
        unanswered.push(entries[i].index + 1);
        entries[i].fieldset.classList.add("spepi-quiz-question--unanswered");
      }
    }

    if (unanswered.length > 0) {
      renderQuestionListMessage(warning, T.unansweredWarningPrefix, instanceId, unanswered);
      warning.removeAttribute("hidden");
      summary.setAttribute("hidden", "hidden");
      return;
    }
    warning.setAttribute("hidden", "hidden");

    var correctCount = 0;
    var incorrectNums = [];

    for (i = 0; i < entries.length; i++) {
      var entry = entries[i];
      var q = entry.question;
      var isCorrect = answers[i] === q.answer;
      if (isCorrect) {
        correctCount++;
      }

      entry.feedback.innerHTML = "";
      entry.feedback.removeAttribute("hidden");

      if (isCorrect) {
        entry.fieldset.className = "spepi-quiz-question spepi-quiz-question--correct";
        entry.feedback.appendChild(el("p", { className: "spepi-quiz-feedback-header", text: T.correct }));
      } else {
        entry.fieldset.className = "spepi-quiz-question spepi-quiz-question--incorrect";
        incorrectNums.push(entry.index + 1);
        var correctText = q.choices[q.answer];
        entry.feedback.appendChild(
          el("p", {
            className: "spepi-quiz-feedback-header",
            text: T.incorrect(correctText)
          })
        );
      }

      if (q.explanation) {
        entry.feedback.appendChild(
          el("p", { className: "spepi-quiz-explanation", text: T.explanation(q.explanation) })
        );
      }
    }

    var passLine = Math.ceil(entries.length * passRatio);
    var passed = correctCount >= passLine;

    summary.innerHTML = "";
    summary.removeAttribute("hidden");
    summary.appendChild(
      el("p", {
        className: "spepi-quiz-score",
        // 自己チェック(gateなし)は合否を持たないため合格ラインを表示しない
        text: gate
          ? T.scoreWithGate(correctCount, entries.length, passLine)
          : T.scoreNoGate(correctCount, entries.length)
      })
    );

    // 不正解一覧はgateの有無(章末クイズ/自己チェック)を問わず表示する。
    if (incorrectNums.length > 0) {
      var incorrectP = el("p", { className: "spepi-quiz-incorrect-list" });
      renderQuestionListMessage(incorrectP, T.incorrectListPrefix, instanceId, incorrectNums);
      summary.appendChild(incorrectP);
    }

    if (gate) {
      var resultP = el("p", { className: "spepi-quiz-result-message" });
      if (passed) {
        resultP.className += " spepi-quiz-result-message--pass";
        resultP.textContent = T.pass;
        if (SPEPI) {
          SPEPI.setPassed(gate);
          try {
            document.dispatchEvent(new CustomEvent("spepi:passed", { detail: { chapter: gate } }));
          } catch (e) {
            // 古いブラウザでCustomEventのコンストラクタが使えない場合は静かに諦める
          }
        }
      } else {
        resultP.className += " spepi-quiz-result-message--fail";
        var needed = passLine - correctCount;
        resultP.textContent = T.fail(needed);
      }
      summary.appendChild(resultP);
    }
  }

  // 「選択をクリア」ボタンの処理。回答・判定・警告・採点サマリーをすべて取り除き、
  // ページを開き直した直後と同じ見た目に戻す。合格記録(localStorage)や
  // 合格済み注記(spepi-quiz-passed-note、form要素の外側にある)は回答状態ではないため対象外。
  function resetQuiz(entries, warning, summary) {
    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i];

      var radios = entry.fieldset.querySelectorAll('input[type="radio"]');
      for (var r = 0; r < radios.length; r++) {
        radios[r].checked = false;
      }

      entry.feedback.innerHTML = "";
      entry.feedback.setAttribute("hidden", "hidden");

      // 正誤・未回答ハイライトをまとめてクラス指定し直すことで初期状態に戻す。
      entry.fieldset.className = "spepi-quiz-question";
    }

    warning.textContent = "";
    warning.setAttribute("hidden", "hidden");

    summary.innerHTML = "";
    summary.setAttribute("hidden", "hidden");
  }

  function loadQuiz(container) {
    var src = container.getAttribute("data-quiz-src");
    var gate = container.getAttribute("data-quiz-gate") || null;
    if (!src) {
      return;
    }

    if (typeof fetch !== "function") {
      renderMessage(container, "spepi-quiz-error", T.unsupportedBrowser);
      return;
    }

    renderMessage(container, "spepi-quiz-loading", T.loading);

    fetch(src)
      .then(function (res) {
        if (!res.ok) {
          throw new Error("HTTP " + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.questions || !data.questions.length) {
          throw new Error("empty-quiz-data");
        }
        buildQuiz(container, data, gate);
      })
      .catch(function () {
        var label = gate ? chapterLabelFor(gate) + "の" : "";
        renderMessage(container, "spepi-quiz-error", T.loadError(label));
      });
  }

  ready(function () {
    var containers = document.querySelectorAll("[data-quiz-src]");
    for (var i = 0; i < containers.length; i++) {
      loadQuiz(containers[i]);
    }
  });
})();
