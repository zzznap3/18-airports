"""全3125通りの回答で、各作品が何回結果になるかを数える。questions.json を調整したら実行。"""
import json, itertools, collections, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
q = json.load(open(ROOT/'data/questions.json', encoding='utf-8'))['questions']
works = json.load(open(ROOT/'data/works.json', encoding='utf-8'))

def pick(ans):  # assets/quiz.js の decide() と同じ処理
    s = collections.Counter()
    for qi, a in enumerate(ans):
        for k, v in q[qi]['options'][a]['scores'].items():
            s[int(k)] += v
    m = max(s.values())
    tied = sorted(k for k, v in s.items() if v == m)
    h = 0
    for a in ans:
        h = (h * 31 + a + 1) % 1000003
    return tied[h % len(tied)]

combos = list(itertools.product(*[range(len(x['options'])) for x in q]))
c = collections.Counter(pick(a) for a in combos)
for i in range(1, len(works) + 1):
    n = c[i]
    print(f"{i:>2} {n:>4} {n/len(combos)*100:5.1f}%  {'#'*(n//10)}  {works[f'作品{i}']['タイトル']}")
