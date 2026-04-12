
"""
Motor semântico para o Sistema Folksonomia Digital.
"""

from __future__ import annotations

import json
import os
import re
import hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import AgglomerativeClustering
    SKLEARN_AVAILABLE = True
except Exception:
    TfidfVectorizer = None
    LogisticRegression = None
    Pipeline = None
    cosine_similarity = None
    AgglomerativeClustering = None
    SKLEARN_AVAILABLE = False


MATERIAL_LEXICON = [
    "ouro",
    "prata",
    "bronze",
    "cobre",
    "ferro",
    "aço",
    "latão",
    "estanho",
    "alumínio",
    "chumbo",
    "madeira",
    "cedro",
    "mogno",
    "jacarandá",
    "carvalho",
    "pinho",
    "bambu",
    "palha",
    "vime",
    "cortiça",
    "barro",
    "argila",
    "terracota",
    "cerâmica",
    "porcelana",
    "faiança",
    "gesso",
    "estuque",
    "mármore",
    "granito",
    "pedra",
    "ardósia",
    "basalto",
    "calcário",
    "areia",
    "vidro",
    "cristal",
    "espelho",
    "acrílico",
    "resina",
    "plástico",
    "baquelite",
    "borracha",
    "silicone",
    "látex",
    "papel",
    "papelão",
    "cartão",
    "pergaminho",
    "couro",
    "pele",
    "tecido",
    "algodão",
    "linho",
    "seda",
    "veludo",
    "lã",
    "crochê",
    "tricô",
    "renda",
    "bordado",
    "miçanga",
    "conta",
    "pérola",
    "marfim",
    "osso",
    "concha",
    "madrepérola",
    "fibra",
    "fibra vegetal",
    "fibra sintética",
    "poliéster",
    "nylon",
    "cetim",
    "denim",
    "jeans",
    "tinta a óleo",
    "têmpera",
    "guache",
    "aquarela",
    "acrílica",
    "pastel",
    "grafite",
    "carvão",
    "nanquim",
    "pigmento",
    "verniz",
    "esmalte",
    "betume",
    "folha de ouro",
    "folha de prata",
    "papiro",
    "cemento",
    "concreto",
    "cimento",
    "cimento armado",
    "azulejo",
    "mosaico",
    "terracota esmaltada",
    "sisal"
]

TECHNIQUE_LEXICON = [
    "pintura",
    "escultura",
    "gravura",
    "xilogravura",
    "litografia",
    "serigrafia",
    "fotografia",
    "colagem",
    "assemblage",
    "desenho",
    "aquarela",
    "guache",
    "têmpera",
    "óleo sobre tela",
    "óleo sobre madeira",
    "acrílica sobre tela",
    "afresco",
    "mosaico",
    "entalhe",
    "fundição",
    "modelagem",
    "cerâmica",
    "torneamento",
    "bordado",
    "tecelagem",
    "costura",
    "crochê",
    "tricô",
    "marchetaria",
    "ourivesaria",
    "cinzelagem",
    "repuxo",
    "esmaltagem",
    "lacagem",
    "fotomontagem",
    "instalação",
    "performance",
    "videoarte",
    "arte digital",
    "impressão 3d",
    "projeção",
    "arte sonora",
    "caligrafia",
    "ilustração",
    "encadernação",
    "restauro",
    "conservação",
    "digitalização",
    "fotogrametria",
    "scanner 3d",
    "catalogação",
    "indexação",
    "classificação",
    "documentação museológica",
    "curadoria",
    "mediação",
    "anotação colaborativa",
    "folksonomia",
    "rotulagem social",
    "machine learning"
]

THEME_LEXICON = [
    "religião",
    "catolicismo",
    "devoção",
    "santo",
    "igreja",
    "mitologia",
    "guerra",
    "paz",
    "violência",
    "trabalho",
    "família",
    "maternidade",
    "paternidade",
    "infância",
    "velhice",
    "ancestralidade",
    "memória",
    "identidade",
    "raça",
    "gênero",
    "mulher",
    "homem",
    "liderança feminina",
    "chefia de família",
    "território",
    "cidade",
    "campo",
    "paisagem",
    "natureza",
    "mar",
    "rio",
    "montanha",
    "céu",
    "noite",
    "dia",
    "morte",
    "vida",
    "resistência",
    "colonialismo",
    "escravidão",
    "liberdade",
    "migração",
    "ritual",
    "festa",
    "luto",
    "amor",
    "solidão",
    "poder",
    "política",
    "justiça",
    "pobreza",
    "riqueza",
    "espiritualidade",
    "cotidiano",
    "tecnologia",
    "ciência",
    "saúde",
    "educação",
    "tradição",
    "modernidade",
    "barroco",
    "renascimento",
    "romantismo",
    "impressionismo",
    "expressionismo",
    "surrealismo",
    "abstração",
    "figurativo",
    "patrimônio",
    "museu",
    "acervo",
    "documentação",
    "arquivo",
    "enciclopédia",
    "conhecimento",
    "descoberta",
    "navegação",
    "busca",
    "participação",
    "colaboração",
    "acessibilidade",
    "inclusão",
    "diversidade",
    "afro-brasileiro",
    "indígena",
    "popular",
    "urbano",
    "rural",
    "trabalho doméstico",
    "cuidado"
]

PERIOD_LEXICON = [
    "pré-história",
    "antiguidade",
    "idade média",
    "renascimento",
    "barroco",
    "rococó",
    "neoclassicismo",
    "romantismo",
    "realismo",
    "simbolismo",
    "art nouveau",
    "modernismo",
    "contemporâneo",
    "século xvi",
    "século xvii",
    "século xviii",
    "século xix",
    "século xx",
    "século xxi",
    "colonial",
    "imperial",
    "república velha",
    "ditadura",
    "redemocratização",
    "período joanino",
    "primeira república",
    "segunda guerra",
    "entre-guerras"
]

PLACE_LEXICON = [
    "rio de janeiro",
    "são paulo",
    "bahia",
    "minas gerais",
    "pernambuco",
    "lisboa",
    "madrid",
    "paris",
    "roma",
    "florença",
    "sevilha",
    "porto",
    "brasil",
    "portugal",
    "espanha",
    "frança",
    "itália",
    "américa latina",
    "africa",
    "europa",
    "museu do prado",
    "unirio",
    "fiocruz",
    "museu nacional",
    "museu de arte moderna",
    "museu histórico nacional",
    "niterói",
    "salvador",
    "recife",
    "ouro preto"
]

ICONOGRAPHY_LEXICON = [
    "virgem maria",
    "nossa senhora",
    "maria",
    "cristo",
    "jesus",
    "anjos",
    "cruz",
    "coroa",
    "espada",
    "cálice",
    "cavaleiro",
    "navio",
    "barco",
    "casa",
    "janela",
    "mesa",
    "cadeira",
    "árvore",
    "flor",
    "fruta",
    "animal",
    "pássaro",
    "cavalo",
    "boi",
    "cobra",
    "peixe",
    "onça",
    "sol",
    "lua",
    "estrela",
    "mãe",
    "criança",
    "família",
    "mulher negra",
    "homem negro",
    "santo antônio",
    "são jorge",
    "madona",
    "autorretrato",
    "retrato"
]

ENTITY_TYPE_NAMES = [
    "pessoa",
    "lugar",
    "período",
    "material",
    "técnica",
    "iconografia",
    "tema",
    "evento",
    "grupo social",
    "conceito"
]


STOPWORDS_PT = [
    "a","o","os","as","de","da","do","das","dos","e","ou","em","no","na","nos","nas",
    "um","uma","uns","umas","por","para","com","sem","sob","sobre","ao","aos","à","às",
    "que","se","é","ser","foi","são","era","como","mais","menos","muito","muita","muitos",
    "muitas","já","ainda","também","não","sim","talvez","depois","antes","entre","até",
]

SYNONYM_SETS = [
    {"nossa senhora","virgem maria","maria","madona"},
    {"afro brasileiro","afro-brasileiro","afrobrasileiro"},
    {"século xix","sec xix","séc xix","19th century","dezenove"},
    {"século xx","sec xx","séc xx","20th century","vinte"},
    {"óleo sobre tela","oleo sobre tela","pintura a óleo","tinta a óleo"},
    {"rio de janeiro","rio","cidade do rio de janeiro"},
    {"documentação museológica","documentacao museologica","documentação","catalogação museológica"},
    {"folksonomia","folksonomia museológica","rotulagem social","social tagging"},
    {"mulher","mulheres","feminino","liderança feminina"},
    {"barroco","estilo barroco","período barroco"},
]

ENTITY_PATTERNS = {
    "material": MATERIAL_LEXICON,
    "técnica": TECHNIQUE_LEXICON,
    "tema": THEME_LEXICON,
    "período": PERIOD_LEXICON,
    "lugar": PLACE_LEXICON,
    "iconografia": ICONOGRAPHY_LEXICON,
}

@dataclass
class SemanticTagSuggestion:
    tag_original: str
    tag_normalizada: str
    tipo_entidade: str
    conceito_sugerido: str
    confianca: float
    justificativa: str
    relacionados: List[str] = field(default_factory=list)
    ambiguo: bool = False


@dataclass
class ValidationRecord:
    tag_original: str
    tag_normalizada: str
    approved_entity_type: str
    approved_concept: str
    approved: bool
    validated_by: str
    timestamp: str
    notes: str = ""


@dataclass
class AutomationResult:
    ran_at: str
    pending_tags: int
    trained_samples: int
    concepts_created: int
    relations_created: int
    clusters_created: int
    report: Dict[str, Any] = field(default_factory=dict)


def ensure_dir(path: os.PathLike[str] | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path: os.PathLike[str] | str, default: Any) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: os.PathLike[str] | str, data: Any) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text).strip().lower()
    replacements = {
        "á":"a","à":"a","â":"a","ã":"a",
        "é":"e","ê":"e",
        "í":"i",
        "ó":"o","ô":"o","õ":"o",
        "ú":"u",
        "ç":"c",
    }
    for src, tgt in replacements.items():
        text = text.replace(src, tgt)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> List[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [tok for tok in tokens if tok and tok not in STOPWORDS_PT]


def char_ngrams(text: str, n: int = 3) -> set[str]:
    text = normalize_text(text)
    if len(text) < n:
        return {text} if text else set()
    return {text[i:i+n] for i in range(len(text)-n+1)}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def lexical_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.8 * (min(len(na), len(nb)) / max(len(na), len(nb)))
    tok_score = jaccard(tokenize(na), tokenize(nb))
    ng_score = jaccard(char_ngrams(na), char_ngrams(nb))
    return round(0.6 * ng_score + 0.4 * tok_score, 4)


def match_synonym_set(text: str) -> Optional[str]:
    nt = normalize_text(text)
    for group in SYNONYM_SETS:
        normalized_group = {normalize_text(x) for x in group}
        if nt in normalized_group:
            return sorted(group, key=len, reverse=True)[0]
    return None


def infer_entity_type_rule(text: str) -> Tuple[str, float, str]:
    nt = normalize_text(text)
    if not nt:
        return "conceito", 0.0, "Texto vazio"
    for entity_type, lexicon in ENTITY_PATTERNS.items():
        if nt in [normalize_text(x) for x in lexicon]:
            return entity_type, 0.97, f"Correspondência direta no léxico de {entity_type}"
    token_set = set(tokenize(nt))
    for entity_type, lexicon in ENTITY_PATTERNS.items():
        lex_tokens = [set(tokenize(x)) for x in lexicon]
        score = max((jaccard(token_set, lt) for lt in lex_tokens), default=0.0)
        if score >= 0.75:
            return entity_type, min(0.92, 0.65 + score / 2), f"Similaridade alta com vocabulário de {entity_type}"
    if re.search(r"\b(seculo|sec|séc|xv|xvi|xvii|xviii|xix|xx|xxi)\b", nt):
        return "período", 0.81, "Padrão temporal detectado"
    if any(word in nt for word in ["rio", "cidade", "bairro", "museu", "brasil", "portugal", "franca", "espanha"]):
        return "lugar", 0.64, "Padrões toponímicos detectados"
    if any(word in nt for word in ["tela", "oleo", "aquarela", "escultura", "gravura", "fotografia"]):
        return "técnica", 0.74, "Termos de técnica detectados"
    if any(word in nt for word in ["ouro", "prata", "madeira", "barro", "argila", "papel", "tecido"]):
        return "material", 0.74, "Termos de material detectados"
    if any(word in nt for word in ["mulher", "familia", "guerra", "religiao", "memoria", "ancestralidade", "identidade"]):
        return "tema", 0.61, "Termos temáticos detectados"
    return "conceito", 0.35, "Sem correspondência forte; tratado como conceito livre"


class SemanticKnowledgeBase:
    def __init__(self, base_dir: os.PathLike[str] | str):
        self.base_dir = ensure_dir(base_dir)
        self.semantic_dir = ensure_dir(self.base_dir / "semantic")
        self.models_dir = ensure_dir(self.base_dir / "models")
        self.concepts_path = self.semantic_dir / "conceitos.json"
        self.validations_path = self.semantic_dir / "validacoes.json"
        self.relations_path = self.semantic_dir / "relacoes.json"
        self.training_examples_path = self.semantic_dir / "exemplos_treinamento.json"
        self.automation_log_path = self.semantic_dir / "automation_log.json"
        self.model_meta_path = self.models_dir / "model_meta.json"
        self.concept_store = load_json(self.concepts_path, [])
        self.validation_store = load_json(self.validations_path, [])
        self.relation_store = load_json(self.relations_path, [])
        self.learning_examples = load_json(self.training_examples_path, [])
        self.automation_log = load_json(self.automation_log_path, [])
        self.classifier_bundle: Optional[Pipeline] = None
        self.concept_vectorizer: Optional[TfidfVectorizer] = None
        self.concept_matrix = None
        self._refresh_caches()

    def _refresh_caches(self) -> None:
        self._concept_names = [c.get("preferred_label", "") for c in self.concept_store]
        if SKLEARN_AVAILABLE and self._concept_names:
            self.concept_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))
            self.concept_matrix = self.concept_vectorizer.fit_transform(self._concept_names)
        else:
            self.concept_vectorizer = None
            self.concept_matrix = None

    def save_all(self) -> None:
        save_json(self.concepts_path, self.concept_store)
        save_json(self.validations_path, self.validation_store)
        save_json(self.relations_path, self.relation_store)
        save_json(self.training_examples_path, self.learning_examples)
        save_json(self.automation_log_path, self.automation_log)

    def upsert_concept(self, preferred_label: str, entity_type: str = "conceito", aliases: Optional[List[str]] = None, description: str = "", external_uri: str = "", source: str = "sistema") -> Dict[str, Any]:
        preferred_label = preferred_label.strip()
        aliases = aliases or []
        normalized = normalize_text(preferred_label)
        for concept in self.concept_store:
            if normalize_text(concept.get("preferred_label", "")) == normalized:
                existing_aliases = set(concept.get("aliases", []))
                existing_aliases.update([a for a in aliases if a])
                concept["aliases"] = sorted(existing_aliases)
                if entity_type and concept.get("entity_type") in ["", "conceito"]:
                    concept["entity_type"] = entity_type
                if description and not concept.get("description"):
                    concept["description"] = description
                if external_uri and not concept.get("external_uri"):
                    concept["external_uri"] = external_uri
                concept["updated_at"] = datetime.now().isoformat()
                self.save_all()
                self._refresh_caches()
                return concept
        concept = {
            "id": hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16],
            "preferred_label": preferred_label,
            "normalized_label": normalized,
            "aliases": sorted(set(aliases)),
            "entity_type": entity_type,
            "description": description,
            "external_uri": external_uri,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "usage_count": 0,
        }
        self.concept_store.append(concept)
        self.save_all()
        self._refresh_caches()
        return concept

    def record_usage(self, concept_id: str) -> None:
        for concept in self.concept_store:
            if concept["id"] == concept_id:
                concept["usage_count"] = int(concept.get("usage_count", 0)) + 1
                concept["updated_at"] = datetime.now().isoformat()
                break
        self.save_all()

    def find_best_concept_match(self, text: str) -> Tuple[Optional[Dict[str, Any]], float]:
        nt = normalize_text(text)
        if not nt:
            return None, 0.0
        for concept in self.concept_store:
            labels = [concept.get("preferred_label", "")] + concept.get("aliases", [])
            for label in labels:
                sim = lexical_similarity(nt, label)
                if sim >= 0.95:
                    return concept, sim
        if SKLEARN_AVAILABLE and self.concept_vectorizer is not None and self.concept_matrix is not None:
            query = self.concept_vectorizer.transform([text])
            sims = cosine_similarity(query, self.concept_matrix)[0]
            idx = int(np.argmax(sims))
            best = float(sims[idx])
            if best >= 0.35:
                return self.concept_store[idx], best
        best_concept = None
        best_score = 0.0
        for concept in self.concept_store:
            labels = [concept.get("preferred_label", "")] + concept.get("aliases", [])
            score = max((lexical_similarity(nt, lb) for lb in labels), default=0.0)
            if score > best_score:
                best_score = score
                best_concept = concept
        return best_concept, best_score

    def record_validation(self, tag_original: str, tag_normalizada: str, approved_entity_type: str, approved_concept: str, approved: bool, validated_by: str, notes: str = "") -> Dict[str, Any]:
        record = asdict(ValidationRecord(tag_original=tag_original, tag_normalizada=tag_normalizada, approved_entity_type=approved_entity_type, approved_concept=approved_concept, approved=approved, validated_by=validated_by, timestamp=datetime.now().isoformat(), notes=notes))
        self.validation_store.append(record)
        self.learning_examples.append(record)
        if approved and approved_concept:
            concept = self.upsert_concept(preferred_label=approved_concept, entity_type=approved_entity_type, aliases=[tag_original, tag_normalizada], source=f"validado:{validated_by}")
            self.record_usage(concept["id"])
        self.save_all()
        return record

    def relation_exists(self, source: str, target: str, relation_type: str) -> bool:
        ns = normalize_text(source)
        nt = normalize_text(target)
        for rel in self.relation_store:
            if normalize_text(rel.get("source", "")) == ns and normalize_text(rel.get("target", "")) == nt and rel.get("relation_type") == relation_type:
                return True
        return False

    def add_relation(self, source: str, target: str, relation_type: str, confidence: float, evidence: str, validated: bool = False) -> Optional[Dict[str, Any]]:
        if not source or not target or normalize_text(source) == normalize_text(target):
            return None
        if self.relation_exists(source, target, relation_type):
            return None
        rel = {
            "id": hashlib.sha1(f"{source}|{target}|{relation_type}".encode("utf-8")).hexdigest()[:18],
            "source": source,
            "target": target,
            "relation_type": relation_type,
            "confidence": round(float(confidence), 4),
            "evidence": evidence,
            "validated": validated,
            "created_at": datetime.now().isoformat(),
        }
        self.relation_store.append(rel)
        self.save_all()
        return rel

    def train_entity_classifier(self) -> Dict[str, Any]:
        examples = [ex for ex in self.learning_examples if ex.get("approved")]
        labels = [ex.get("approved_entity_type", "") for ex in examples if ex.get("approved_entity_type")]
        texts = [ex.get("tag_original") or ex.get("tag_normalizada") for ex in examples if ex.get("approved_entity_type")]
        if not SKLEARN_AVAILABLE:
            meta = {"trained": False, "reason": "sklearn não disponível", "samples": len(texts)}
            save_json(self.model_meta_path, meta)
            return meta
        if len(set(labels)) < 2 or len(texts) < 6:
            meta = {"trained": False, "reason": "amostras insuficientes", "samples": len(texts)}
            save_json(self.model_meta_path, meta)
            return meta
        bundle = Pipeline([("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))), ("clf", LogisticRegression(max_iter=600, class_weight="balanced"))])
        bundle.fit(texts, labels)
        self.classifier_bundle = bundle
        meta = {"trained": True, "samples": len(texts), "classes": sorted(set(labels)), "trained_at": datetime.now().isoformat()}
        save_json(self.model_meta_path, meta)
        return meta

    def predict_entity_type_ml(self, text: str) -> Tuple[Optional[str], float, str]:
        if self.classifier_bundle is None:
            return None, 0.0, "Modelo supervisionado ainda não treinado"
        try:
            probs = self.classifier_bundle.predict_proba([text])[0]
            classes = self.classifier_bundle.classes_
            idx = int(np.argmax(probs))
            label = str(classes[idx])
            prob = float(probs[idx])
            return label, prob, "Predição supervisionada"
        except Exception:
            return None, 0.0, "Falha ao predizer com o modelo"

    def related_terms(self, text: str, top_k: int = 8) -> List[Dict[str, Any]]:
        text = normalize_text(text)
        candidates = set()
        for lexicon in [MATERIAL_LEXICON, TECHNIQUE_LEXICON, THEME_LEXICON, PERIOD_LEXICON, PLACE_LEXICON, ICONOGRAPHY_LEXICON]:
            candidates.update(lexicon)
        for concept in self.concept_store:
            candidates.add(concept.get("preferred_label", ""))
            candidates.update(concept.get("aliases", []))
        scores = []
        for term in candidates:
            if not term:
                continue
            score = lexical_similarity(text, term)
            if score >= 0.18 and normalize_text(term) != text:
                scores.append({"term": term, "score": round(score, 4)})
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def suggest_semantics(self, text: str) -> SemanticTagSuggestion:
        text = text or ""
        tag_norm = normalize_text(text)
        synonym = match_synonym_set(tag_norm)
        rule_type, rule_conf, rule_why = infer_entity_type_rule(tag_norm)
        ml_type, ml_conf, ml_why = self.predict_entity_type_ml(text)
        final_type = rule_type
        final_conf = rule_conf
        why_parts = [rule_why]
        if ml_type and ml_conf > final_conf + 0.08:
            final_type = ml_type
            final_conf = ml_conf
            why_parts.append(ml_why)
        concept_match, concept_score = self.find_best_concept_match(tag_norm)
        relacionados = self.related_terms(tag_norm, top_k=8)
        ambiguo = False
        if synonym and normalize_text(synonym) != tag_norm:
            concept_name = synonym
            final_conf = max(final_conf, 0.83)
            why_parts.append("Sinônimo reconhecido no dicionário local")
        elif concept_match and concept_score >= 0.45:
            concept_name = concept_match.get("preferred_label", text)
            final_conf = max(final_conf, float(concept_score))
            why_parts.append("Conceito reconciliado na base local")
            if concept_match.get("entity_type") not in ["", "conceito"]:
                final_type = concept_match.get("entity_type")
        else:
            concept_name = text.strip().title() if text.strip() else ""
        if len(relacionados) >= 3:
            top_scores = [r["score"] for r in relacionados[:3]]
            spread = max(top_scores) - min(top_scores)
            if spread < 0.12 and final_conf < 0.85:
                ambiguo = True
                why_parts.append("Há mais de uma interpretação plausível")
        return SemanticTagSuggestion(tag_original=text, tag_normalizada=tag_norm, tipo_entidade=final_type, conceito_sugerido=concept_name, confianca=round(float(final_conf), 4), justificativa="; ".join([w for w in why_parts if w]), relacionados=[r["term"] for r in relacionados], ambiguo=ambiguo)

    def cluster_terms(self, terms: Sequence[str], threshold: float = 0.56) -> List[List[str]]:
        uniq = sorted({normalize_text(t) for t in terms if normalize_text(t)})
        if len(uniq) <= 1:
            return []
        if SKLEARN_AVAILABLE and len(uniq) >= 3:
            vect = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))
            X = vect.fit_transform(uniq).toarray()
            distance_threshold = max(0.05, 1 - threshold)
            try:
                clusterer = AgglomerativeClustering(n_clusters=None, distance_threshold=distance_threshold, metric="cosine", linkage="average")
                labels = clusterer.fit_predict(X)
                groups = defaultdict(list)
                for label, term in zip(labels, uniq):
                    groups[int(label)].append(term)
                result = [sorted(v) for v in groups.values() if len(v) > 1]
                return sorted(result, key=len, reverse=True)
            except Exception:
                pass
        parent = {t: t for t in uniq}
        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                sim = lexical_similarity(uniq[i], uniq[j])
                if sim >= threshold:
                    union(uniq[i], uniq[j])
        groups = defaultdict(list)
        for term in uniq:
            groups[find(term)].append(term)
        return [sorted(v) for v in groups.values() if len(v) > 1]

    def build_tag_relations(self, tags_df: pd.DataFrame, threshold: float = 0.58) -> List[Dict[str, Any]]:
        if tags_df.empty or "tag" not in tags_df.columns:
            return []
        tags = [normalize_text(t) for t in tags_df["tag"].dropna().tolist() if normalize_text(t)]
        created = []
        for cluster in self.cluster_terms(tags, threshold=threshold):
            anchor = sorted(cluster, key=len, reverse=True)[0]
            for term in cluster:
                if term == anchor:
                    continue
                rel = self.add_relation(source=term, target=anchor, relation_type="aproxima_se_de", confidence=lexical_similarity(term, anchor), evidence="cluster_semantico_automatico", validated=False)
                if rel:
                    created.append(rel)
        return created

    def concept_gap_report(self, tags_df: pd.DataFrame) -> Dict[str, Any]:
        if tags_df.empty:
            return {"sem_conceito": [], "total_tags": 0, "cobertura": 0.0}
        unresolved = []
        matched = 0
        for tag in tags_df["tag"].dropna().tolist():
            concept, score = self.find_best_concept_match(tag)
            if concept and score >= 0.45:
                matched += 1
            else:
                unresolved.append(tag)
        total = len(tags_df)
        coverage = matched / total if total else 0.0
        return {"sem_conceito": Counter(unresolved).most_common(40), "total_tags": total, "cobertura": round(coverage, 4)}

    def build_semantic_graph(self, obras_df: pd.DataFrame, tags_df: pd.DataFrame) -> Dict[str, Any]:
        nodes = []
        edges = []
        seen = set()
        if not obras_df.empty:
            for _, row in obras_df.iterrows():
                node_id = f"obra:{row['id']}"
                nodes.append({"id": node_id, "label": str(row.get("titulo", f"Obra {row['id']}")), "type": "obra"})
                seen.add(node_id)
        if not tags_df.empty:
            for _, row in tags_df.iterrows():
                tag = str(row.get("tag", ""))
                obra_id = row.get("obra_id")
                node_id = f"tag:{normalize_text(tag)}"
                if node_id not in seen:
                    suggestion = self.suggest_semantics(tag)
                    nodes.append({"id": node_id, "label": tag, "type": "tag", "entity_type": suggestion.tipo_entidade, "concept": suggestion.conceito_sugerido})
                    seen.add(node_id)
                if obra_id is not None:
                    edges.append({"source": f"obra:{obra_id}", "target": node_id, "relation": "recebeu_tag", "weight": 1.0})
                if suggestion.conceito_sugerido:
                    concept = self.upsert_concept(preferred_label=suggestion.conceito_sugerido, entity_type=suggestion.tipo_entidade, aliases=[tag], source="grafo_automatico")
                    cnode = f"conceito:{concept['id']}"
                    if cnode not in seen:
                        nodes.append({"id": cnode, "label": concept["preferred_label"], "type": "conceito", "entity_type": concept.get("entity_type", "conceito")})
                        seen.add(cnode)
                    edges.append({"source": node_id, "target": cnode, "relation": "aproxima_se_de", "weight": max(0.2, suggestion.confianca)})
        for rel in self.relation_store:
            edges.append({"source": f"tag:{normalize_text(rel['source'])}", "target": f"tag:{normalize_text(rel['target'])}", "relation": rel["relation_type"], "weight": rel.get("confidence", 0.5)})
        return {"nodes": nodes, "edges": edges}

    def run_automation(self, obras_df: pd.DataFrame, tags_df: pd.DataFrame, admin_user: str = "sistema") -> AutomationResult:
        pending_tags = len(tags_df) if not tags_df.empty else 0
        initial_concepts = len(self.concept_store)
        initial_relations = len(self.relation_store)
        if not tags_df.empty:
            for tag in tags_df["tag"].dropna().tolist():
                suggestion = self.suggest_semantics(tag)
                if suggestion.conceito_sugerido:
                    self.upsert_concept(preferred_label=suggestion.conceito_sugerido, entity_type=suggestion.tipo_entidade, aliases=[suggestion.tag_original, suggestion.tag_normalizada], source="automacao")
            created_relations = self.build_tag_relations(tags_df)
        else:
            created_relations = []
        trained = self.train_entity_classifier()
        gap = self.concept_gap_report(tags_df)
        graph = self.build_semantic_graph(obras_df, tags_df)
        final_concepts = len(self.concept_store)
        final_relations = len(self.relation_store)
        clusters = self.cluster_terms(tags_df["tag"].tolist() if not tags_df.empty else [], threshold=0.58)
        result = AutomationResult(ran_at=datetime.now().isoformat(), pending_tags=pending_tags, trained_samples=int(trained.get("samples", 0) or 0), concepts_created=final_concepts - initial_concepts, relations_created=final_relations - initial_relations, clusters_created=len(clusters), report={"trained": trained, "gap_report": gap, "graph_size": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])}, "clusters_preview": clusters[:15], "admin_user": admin_user, "new_relations": created_relations[:50]})
        self.automation_log.append(asdict(result))
        self.save_all()
        return result

    def export_training_dataset(self) -> pd.DataFrame:
        if not self.learning_examples:
            return pd.DataFrame(columns=["tag_original","tag_normalizada","approved_entity_type","approved_concept","approved","validated_by","timestamp","notes"])
        return pd.DataFrame(self.learning_examples)

    def semantic_summary(self, tags_df: pd.DataFrame) -> Dict[str, Any]:
        if tags_df.empty:
            return {"entity_distribution": {}, "concept_distribution": {}, "ambiguity_rate": 0.0, "top_unresolved": []}
        suggestions = [self.suggest_semantics(t) for t in tags_df["tag"].dropna().tolist()]
        entity_counter = Counter([s.tipo_entidade for s in suggestions])
        concept_counter = Counter([s.conceito_sugerido for s in suggestions if s.conceito_sugerido])
        ambiguity_rate = sum(1 for s in suggestions if s.ambiguo) / max(1, len(suggestions))
        gap = self.concept_gap_report(tags_df)
        return {"entity_distribution": dict(entity_counter), "concept_distribution": dict(concept_counter.most_common(25)), "ambiguity_rate": round(ambiguity_rate, 4), "top_unresolved": gap["sem_conceito"][:20]}


def bootstrap_default_concepts(kb: SemanticKnowledgeBase) -> None:
    seed_entries = []
    for item in MATERIAL_LEXICON:
        seed_entries.append((item.title(), "material"))
    for item in TECHNIQUE_LEXICON:
        seed_entries.append((item.title(), "técnica"))
    for item in THEME_LEXICON:
        seed_entries.append((item.title(), "tema"))
    for item in PERIOD_LEXICON:
        seed_entries.append((item.title(), "período"))
    for item in PLACE_LEXICON:
        seed_entries.append((item.title(), "lugar"))
    for item in ICONOGRAPHY_LEXICON:
        seed_entries.append((item.title(), "iconografia"))
    for label, typ in seed_entries:
        kb.upsert_concept(preferred_label=label, entity_type=typ, aliases=[normalize_text(label)], source="bootstrap")


def dataframe_from_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


__all__ = ["SemanticKnowledgeBase","SemanticTagSuggestion","ValidationRecord","AutomationResult","bootstrap_default_concepts","normalize_text","tokenize","lexical_similarity","infer_entity_type_rule","dataframe_from_records"]
