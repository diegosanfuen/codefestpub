#!bin/sh
python -m scripts.10_build_dataset_from_ops
python -m scripts.11_enrich_family
python -m scripts.12_enrich_legal
python -m scripts.13_enrich_text
python -m scripts.14_enrich_biblio_light
python -m scripts.15_enrich_biblio
python -m scripts.16_enrich_parties
python -m scripts.17_enrich_text
python -m scripts.20_build_final_tables
python -m scripts.21_add_derived_features
python -m scripts.22_relabel_roi_v3
python -m scripts.23_trasform_variables
python -m scripts.24_build_model_tablon
python -m scripts.25_build_nlp_tablon
python -m scripts.26_build_model_tablon_nlp
python -m scripts.27_build_model_tablon_final
python -m scripts.30_model_export_to_pkl

# COPY FINAL MODEL IN WINNER FOLDER
cp ./data/models/ridge_alpha0p3_spearman0p95_v1.pkl ./data/models/winner_model/winner_model_prod.pkl

echo "The final model is on the path: data/models/winner_model/winner_model_prod.pkl"
