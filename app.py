import gradio as gr
import random, itertools, string

# ---------- Nombres ----------
MEN_NAMES   = sorted(["Abe","Ben","Cal","Dan","Eli","Fox","Gus","Hal","Mel","Tom","Zac"])
WOMEN_NAMES = sorted(["Ann","Bea","Cat","Dot","Eve","Fay","Gia","Ivy","Lea","Mia","Tea"])

# ---------- Gale–Shapley ----------
def gale_shapley(men_prefs, women_prefs, proposer="men"):
    if proposer == "women":
        swap = gale_shapley(women_prefs, men_prefs, "men")
        return {v: k for k, v in swap.items()}

    libres = list(men_prefs.keys())
    next_choice = {m: 0 for m in libres}
    engaged = {}                     # mujer -> hombre

    while libres:
        m = libres[0]
        w = men_prefs[m][next_choice[m]]
        next_choice[m] += 1
        if w not in engaged:
            engaged[w] = m
            libres.pop(0)
        else:
            m_cur = engaged[w]
            if women_prefs[w].index(m) < women_prefs[w].index(m_cur):
                engaged[w] = m
                libres[0] = m_cur
    return {m: w for w, m in engaged.items()}

# ---------- Preferencias ----------
def generate_prefs(n, mode):
    men   = MEN_NAMES[:n]
    women = WOMEN_NAMES[:n]
    men_prefs, women_prefs = {}, {}

    if mode == "Random":
        for m in men:   men_prefs[m]   = random.sample(women, n)
        for w in women: women_prefs[w] = random.sample(men,   n)

    elif mode == "Utopía":
        parejas = random.sample(women, n)
        for m, w in zip(men, parejas):
            men_prefs[m]   = [w] + random.sample([x for x in women if x != w], n-1)
            women_prefs[w] = [m] + random.sample([x for x in men   if x != m], n-1)
        for w in women:
            women_prefs.setdefault(w, random.sample(men, n))

    elif mode == "Distopía":
        orden_w = random.sample(women, n)
        orden_m = random.sample(men,   n)
        for m in men:   men_prefs[m]   = orden_w[:]
        for w in women: women_prefs[w] = orden_m[:]

    else:
        raise ValueError("Modo desconocido")

    return men, women, men_prefs, women_prefs

# ---------- Nostalgia ----------
def calc_nostalgia(match, men_prefs, women_prefs):
    men_n   = sum(men_prefs[m].index(w) + 1 for m, w in match.items())
    women_n = sum(women_prefs[w].index(m) + 1 for m, w in match.items())
    return men_n, women_n, men_n + women_n

# ---------- Estabilidad y enumeración ----------
def is_stable(match, men_prefs, women_prefs):
    inv = {w: m for m, w in match.items()}
    for m, w in match.items():
        # hombre prefiere a otra mujer y esta lo prefiere
        for w2 in men_prefs[m][:men_prefs[m].index(w)]:
            if women_prefs[w2].index(m) < women_prefs[w2].index(inv[w2]):
                return False
        # mujer prefiere a otro hombre y este la prefiere
        for m2 in women_prefs[w][:women_prefs[w].index(m)]:
            w2 = match[m2]
            if men_prefs[m2].index(w) < men_prefs[m2].index(w2):
                return False
    return True

def all_stable_matches(n, men, women, men_prefs, women_prefs):
    estables = []
    for perm in itertools.permutations(women):
        match = dict(zip(men, perm))
        if is_stable(match, men_prefs, women_prefs):
            estables.append(match)
    return estables

# ---------- HTML helpers ----------
def prefs_html(men_prefs, women_prefs):
    def tabla(titulo, prefs, quien):
        cab = "".join(f"<th>{i}</th>" for i in range(1, len(next(iter(prefs.values())))+1))
        filas = "".join(
            f"<tr><td><b>{p}</b></td>{''.join(f'<td>{x}</td>' for x in lst)}</tr>"
            for p, lst in prefs.items()
        )
        return f"<div><h4>{titulo}</h4><table border='1'><tr><th>{quien}</th>{cab}</tr>{filas}</table></div>"
    return (
        "<div style='display:flex;gap:24px'>"
        f"{tabla('Preferencias de los hombres', men_prefs, 'Hombre')}"
        f"{tabla('Preferencias de las mujeres', women_prefs, 'Mujer')}"
        "</div>"
    )

def match_html(titulo, match, color):
    filas = "".join(f"<tr><td>{m}</td><td style='color:{color};font-weight:bold'>{w}</td></tr>"
                    for m, w in match.items())
    return f"<div><h4>{titulo}</h4><table border='1'><tr><th>Hombre</th><th>Mujer</th></tr>{filas}</table></div>"

def extreme_matchings_html(lab_M, M, lab_W, W):
    return (
        "<div style='display:flex;gap:40px'>"
        f"{match_html(f'Proponen mujeres ({lab_W})', W, '#e76f51')}"
        f"{match_html(f'Proponen hombres ({lab_M})', M, '#2a9d8f')}"
        "</div>"
    )

def stable_table_html(labeled):
    cab = ("<tr><th>Etiqueta</th><th>Emparejamiento</th>"
           "<th>Nostalgia hombres</th><th>Nostalgia mujeres</th><th>Nostalgia total</th></tr>")
    filas = ""
    for lbl, match, (n_h, n_m, n_t) in labeled:
        parejas = ", ".join(f"{m}-{w}" for m, w in match.items())
        filas += f"<tr><td>{lbl}</td><td>{parejas}</td><td>{n_h}</td><td>{n_m}</td><td>{n_t}</td></tr>"
    return f"<h3>Emparejamientos estables (ordenados por nostalgia femenina)</h3><table border='1'>{cab}{filas}</table>"

# ---------- Utilidad para clave canónica ----------
def match_key(match):
    return tuple(sorted(match.items()))

# ---------- Simulación (CORREGIDO) ----------
def simulate(n, mode):
    men, women, men_prefs, women_prefs = generate_prefs(n, mode)

    # Matchings extremos
    M = gale_shapley(men_prefs, women_prefs, "men")
    W = gale_shapley(men_prefs, women_prefs, "women")

    # Todas las coincidencias estables + nostalgia
    stables = all_stable_matches(n, men, women, men_prefs, women_prefs)
    datos   = [(m, calc_nostalgia(m, men_prefs, women_prefs)) for m in stables]
    datos.sort(key=lambda x: x[1][1])  # ordenar por nostalgia femenina

    # Etiquetas A, B, C...
    labeled = [(string.ascii_uppercase[i], m, r) for i, (m, r) in enumerate(datos)]

    # Diccionario matching->etiqueta
    etiquetas = {match_key(m): lbl for lbl, m, _ in labeled}

    # ---------- construir html ----------
    html_out  = prefs_html(men_prefs, women_prefs)          # <-- ¡inicializado!
    html_out += "<br/>" + extreme_matchings_html(
        etiquetas.get(match_key(M), "?"), M,
        etiquetas.get(match_key(W), "?"), W
    )
    html_out += "<br/>" + stable_table_html(labeled)
    return html_out

# ---------- Interfaz ----------
with gr.Blocks() as demo:
    gr.Image("image.png", show_label=False, height=480)
    with gr.Row():
        n_drop = gr.Dropdown(list(range(3, 11)), label="Número de parejas (N)", value=4)
        mode_drop = gr.Dropdown(
            ["Random", "Utopía", "Distopía"],
            label="Tipo de preferencias",
            value="Random",
        )
        btn = gr.Button("Jugar ▶️", variant="primary")
    out_html = gr.HTML()
    btn.click(simulate, inputs=[n_drop, mode_drop], outputs=out_html)

if __name__ == "__main__":
    # Advertencia: para N=10 la búsqueda exhaustiva puede tardar varios segundos.
    demo.launch()

