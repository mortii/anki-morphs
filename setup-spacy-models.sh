#!/usr/bin/env bash

SPACY_MODELS=(
  ca_core_news_sm
  da_core_news_sm
  de_core_news_md
  el_core_news_sm
  en_core_web_sm
  es_core_news_sm
  fi_core_news_sm
  fr_core_news_sm
  hr_core_news_sm
  it_core_news_sm
  ja_core_news_sm
  ko_core_news_sm
  lt_core_news_sm
  mk_core_news_sm
  nb_core_news_sm
  nl_core_news_sm
  pl_core_news_sm
  pt_core_news_sm
  ro_core_news_sm
  ru_core_news_sm
  sl_core_news_sm
  sv_core_news_sm
  uk_core_news_sm
  zh_core_web_sm
)

echo "Installing spaCy models..."

for m in "${SPACY_MODELS[@]}"; do
  python -m spacy download "$m"
done

echo "spaCy model setup complete."