(() => {
  const $ = (id) => document.getElementById(id);
  let questions = [];
  const answers = [];

  // 回答から作品番号を決める（tools/check_distribution.py と同じ処理）
  function decide() {
    const score = {};
    answers.forEach((a, qi) => {
      for (const [k, v] of Object.entries(questions[qi].options[a].scores)) {
        score[k] = (score[k] || 0) + v;
      }
    });
    const max = Math.max(...Object.values(score));
    const tied = Object.keys(score).filter((k) => score[k] === max).map(Number).sort((a, b) => a - b);
    let h = 0;
    for (const a of answers) h = (h * 31 + a + 1) % 1000003;
    return tied[h % tied.length];
  }

  function render() {
    const i = answers.length;
    const q = questions[i];
    $("count").textContent = `質問 ${i + 1}／${questions.length}`;
    $("ticks").innerHTML = questions
      .map((_, n) => `<li class="${n < i ? "done" : n === i ? "now" : ""}"></li>`)
      .join("");
    $("question").textContent = q.text;
    const list = $("options");
    list.innerHTML = "";
    q.options.forEach((opt, n) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = opt.text;
      b.addEventListener("click", () => choose(n));
      li.appendChild(b);
      list.appendChild(li);
    });
    $("back").hidden = i === 0;
    $("question").focus();
  }

  function choose(n) {
    answers.push(n);
    if (answers.length < questions.length) render();
    else location.href = `result/${decide()}.html`;
  }

  $("back").addEventListener("click", () => {
    answers.pop();
    render();
  });

  $("start").addEventListener("click", async () => {
    try {
      const res = await fetch("data/questions.json", { cache: "no-cache" });
      if (!res.ok) throw new Error(res.status);
      questions = (await res.json()).questions;
    } catch (e) {
      $("intro").insertAdjacentHTML(
        "beforeend",
        '<p class="lead">質問データを読み込めませんでした。ページを再読み込みしてください。</p>'
      );
      return;
    }
    $("intro").hidden = true;
    $("quiz").hidden = false;
    render();
  });
})();
