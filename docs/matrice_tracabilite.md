# Matrice de traçabilité des exigences (RTM)

Générée automatiquement par `python -m tools.rtm` à partir des docstrings des tests.
Un test paramétré (plusieurs cas) compte pour une seule fonction de test.

| Exigence | Prio. | Cas d'util. | Modules | Vérification |
|---|---|---|---|---|
| **BF-01** Créer un compte | Must | UC-01 | `logic/auth.py`, `data/repository.py`, `ui/auth_page.py` | 9 tests automatisés |
| **BF-02** Se connecter et se déconnecter | Must | UC-02 | `logic/auth.py`, `ui/auth_page.py`, `ui/state.py`, `ui/sidebar.py` | 12 tests automatisés |
| **BF-03** Choisir un chapitre | Must | UC-03 | `logic/game_service.py`, `data/repository.py`, `ui/dashboard_page.py` | 6 tests automatisés |
| **BF-04** Répondre aux questions et combattre le boss | Must | UC-04 | `logic/battle.py`, `logic/game_service.py`, `ui/battle_page.py` | 26 tests automatisés |
| **BF-05** Correction et explication après chaque réponse | Must | UC-04 | `logic/battle.py`, `ui/battle_page.py` | 6 tests automatisés |
| **BF-06** Questions choisies selon le niveau et le risque d'oubli | Must | UC-04 | `logic/memory_model.py`, `logic/selector.py`, `logic/game_service.py` | 25 tests automatisés |
| **BF-07** Résultat du combat et concepts à revoir | Must | UC-04 | `logic/battle.py`, `logic/game_service.py`, `ui/result_page.py` | 10 tests automatisés |
| **BF-08** Maîtrise par concept | Must | UC-05 | `logic/memory_model.py`, `logic/game_service.py`, `ui/dashboard_page.py` | 12 tests automatisés |
| **BF-09** Évolution de la maîtrise dans le temps | Should | UC-06 | `logic/game_service.py`, `data/repository.py`, `ui/progress_page.py` | 5 tests automatisés |
| **BF-10** Importer une banque de questions | Must | UC-07 | `logic/importer.py`, `logic/bootstrap.py`, `ui/import_page.py` | 28 tests automatisés |
| **BF-11** Modifier ou supprimer des questions | Could | UC-08 | - | Non réalisé |
| **BNF-01** Performance | Must | - | `logic/selector.py`, `data/repository.py` | 1 test automatisé |
| **BNF-02** Sécurité | Must | - | `logic/auth.py`, `data/repository.py`, `logic/importer.py` | 14 tests automatisés |
| **BNF-03** Usabilité | Should | - | `ui/` | Test manuel |
| **BNF-04** Fiabilité | Must | - | `data/repository.py`, `logic/importer.py`, `logic/game_service.py` | 19 tests automatisés |
| **BNF-05** Maintenabilité | Must | - | `src/ (3 couches)` | 8 tests + vérification complémentaire |
| **BNF-06** Portabilité | Should | - | - | Test manuel |
| **BNF-07** Disponibilité | Should | - | - | Test manuel |
| **BNF-08** Exactitude du modèle d'adaptation | Must | - | `logic/memory_model.py`, `logic/selector.py` | 9 tests + vérification complémentaire |

Remarques :
- **BF-11** : Hors périmètre de cette version (priorité Could).
- **BNF-01** : Mesure sur la logique et la base, hors affichage Streamlit.
- **BNF-03** : Test avec 3 camarades (voir plan de recette).
- **BNF-05** : Rapport de couverture pytest-cov à joindre au rapport.
- **BNF-06** : Test manuel sur Chrome et Firefox, application en ligne.
- **BNF-07** : Vérification avant la présentation.
- **BNF-08** : Tests unitaires ; la simulation contre un ordre aléatoire est un livrable à part.

Tests rattachés à au moins une exigence : 190 ; tests complémentaires (robustesse, modèle de données) : 13.

## Détail : tests par exigence

### BF-01 Créer un compte
- `test_auth.py::test_register_creates_a_student_account`
- `test_auth.py::test_register_refuses_an_existing_username_with_explicit_message`
- `test_auth.py::test_register_refuses_a_short_password`
- `test_auth.py::test_register_refuses_an_absurdly_long_password`
- `test_auth.py::test_register_refuses_invalid_usernames`
- `test_auth.py::test_register_ignores_spaces_around_the_username`
- `test_repository.py::test_create_and_find_a_user`
- `test_repository.py::test_duplicate_username_is_refused`
- `test_ui_acceptance.py::test_registration_is_validated_then_logs_the_new_student_in`

### BF-02 Se connecter et se déconnecter
- `test_auth.py::test_verify_password_accepts_right_and_refuses_wrong`
- `test_auth.py::test_login_with_valid_credentials`
- `test_auth.py::test_login_ignores_username_case`
- `test_auth.py::test_login_failures_all_give_the_same_generic_message`
- `test_bootstrap.py::test_created_accounts_can_log_in_with_the_right_roles`
- `test_integration_battle.py::test_one_students_progress_does_not_leak_to_another`
- `test_repository.py::test_unknown_username_returns_none`
- `test_repository.py::test_masteries_belong_to_one_student`
- `test_ui_acceptance.py::test_the_login_screen_is_shown_first`
- `test_ui_acceptance.py::test_wrong_password_is_refused_with_a_generic_message`
- `test_ui_acceptance.py::test_valid_login_opens_the_dashboard`
- `test_ui_acceptance.py::test_logout_returns_to_the_login_screen`

### BF-03 Choisir un chapitre
- `test_game_service.py::test_cannot_start_a_battle_on_an_empty_chapter`
- `test_game_service.py::test_cannot_start_a_battle_on_an_unknown_chapter`
- `test_game_service.py::test_chapter_list_comes_from_the_database`
- `test_repository.py::test_chapter_list_shows_question_counts`
- `test_repository.py::test_load_questions_only_returns_the_requested_chapter`
- `test_ui_acceptance.py::test_dashboard_lists_the_chapter_with_its_number_of_questions`

### BF-04 Répondre aux questions et combattre le boss
- `test_battle.py::test_new_battle_starts_with_full_boss_and_five_lives`
- `test_battle.py::test_correct_answer_damages_boss_by_difficulty`
- `test_battle.py::test_wrong_answer_costs_one_life_and_spares_the_boss`
- `test_battle.py::test_victory_when_boss_reaches_zero_and_hp_never_negative`
- `test_battle.py::test_last_blow_only_removes_remaining_hp`
- `test_battle.py::test_defeat_when_no_lives_left`
- `test_battle.py::test_cannot_answer_once_the_battle_is_over`
- `test_battle.py::test_running_out_of_questions_is_a_defeat_if_boss_alive`
- `test_battle.py::test_running_out_of_questions_keeps_a_victory`
- `test_bootstrap.py::test_bank_is_not_trivially_guessable`
- `test_game_service.py::test_starting_a_battle_prepares_the_first_question_and_records_it`
- `test_game_service.py::test_correct_answer_hurts_the_boss_and_is_saved`
- `test_game_service.py::test_wrong_answer_costs_a_life_and_returns_the_correction`
- `test_game_service.py::test_victory_is_saved_with_score_and_summary`
- `test_game_service.py::test_defeat_after_five_mistakes_is_saved`
- `test_game_service.py::test_running_out_of_questions_while_the_boss_lives_is_a_defeat`
- `test_integration_battle.py::test_a_perfect_player_wins_and_everything_is_saved`
- `test_integration_battle.py::test_a_player_who_always_fails_loses_after_five_mistakes`
- `test_models.py::test_question_is_correct`
- `test_repository.py::test_question_round_trip`
- `test_selector.py::test_no_question_left_returns_none`
- `test_ui_acceptance.py::test_battle_screen_shows_boss_hit_points_lives_and_a_question`
- `test_ui_acceptance.py::test_wrong_answer_shows_the_correction_and_costs_a_life`
- `test_ui_acceptance.py::test_correct_answer_hurts_the_boss`
- `test_ui_acceptance.py::test_five_mistakes_end_in_a_defeat_screen_with_concepts_to_review`
- `test_ui_acceptance.py::test_answering_correctly_until_the_end_gives_a_victory`

### BF-05 Correction et explication après chaque réponse
- `test_battle.py::test_result_contains_the_correction_and_explanation`
- `test_bootstrap.py::test_bank_questions_are_clean_and_unique`
- `test_bootstrap.py::test_bank_explanations_cite_the_course`
- `test_game_service.py::test_wrong_answer_costs_a_life_and_returns_the_correction`
- `test_game_service.py::test_next_question_requires_an_answer_first`
- `test_ui_acceptance.py::test_wrong_answer_shows_the_correction_and_costs_a_life`

### BF-06 Questions choisies selon le niveau et le risque d'oubli
- `test_battle.py::test_a_question_is_never_asked_twice`
- `test_battle.py::test_answer_updates_the_mastery_of_the_concept`
- `test_battle.py::test_existing_mastery_is_used_as_starting_point`
- `test_bootstrap.py::test_bank_covers_several_concepts_with_all_difficulties`
- `test_game_service.py::test_the_first_question_is_an_easy_one_for_a_new_student`
- `test_game_service.py::test_correct_answer_hurts_the_boss_and_is_saved`
- `test_game_service.py::test_cannot_answer_the_same_question_twice`
- `test_game_service.py::test_questions_are_never_repeated_within_a_battle`
- `test_game_service.py::test_retention_drops_as_days_go_by`
- `test_game_service.py::test_second_battle_continues_from_saved_mastery`
- `test_integration_battle.py::test_a_perfect_player_wins_and_everything_is_saved`
- `test_integration_battle.py::test_no_question_is_asked_twice_in_a_battle`
- `test_integration_battle.py::test_second_battle_starts_from_the_saved_mastery`
- `test_memory_model.py::test_recall_of_never_reviewed_concept_is_zero`
- `test_memory_model.py::test_success_probability_is_half_when_level_equals_difficulty`
- `test_memory_model.py::test_success_probability_increases_with_level`
- `test_memory_model.py::test_success_probability_decreases_with_difficulty`
- `test_memory_model.py::test_a_surprising_success_teaches_more_than_an_expected_one`
- `test_repository.py::test_saving_mastery_again_updates_the_same_row`
- `test_selector.py::test_asked_questions_are_never_chosen`
- `test_selector.py::test_never_reviewed_concept_has_maximal_weight_and_fresh_one_minimal`
- `test_selector.py::test_weight_grows_as_time_passes`
- `test_selector.py::test_weights_are_never_zero`
- `test_selector.py::test_concept_at_risk_is_chosen_much_more_often`
- `test_selector.py::test_difficulty_follows_the_student_level`

### BF-07 Résultat du combat et concepts à revoir
- `test_battle.py::test_score_counts_correct_and_total_answers`
- `test_battle.py::test_weak_concepts_lists_concepts_below_sixty_percent`
- `test_battle.py::test_a_well_mastered_concept_is_not_listed`
- `test_battle.py::test_weak_concepts_are_sorted_from_weakest`
- `test_game_service.py::test_victory_is_saved_with_score_and_summary`
- `test_game_service.py::test_defeat_after_five_mistakes_is_saved`
- `test_repository.py::test_battle_lifecycle_is_recorded`
- `test_repository.py::test_defeat_status_is_stored_without_accent`
- `test_ui_acceptance.py::test_five_mistakes_end_in_a_defeat_screen_with_concepts_to_review`
- `test_ui_acceptance.py::test_answering_correctly_until_the_end_gives_a_victory`

### BF-08 Maîtrise par concept
- `test_game_service.py::test_dashboard_marks_untouched_concepts_as_not_evaluated`
- `test_game_service.py::test_dashboard_shows_level_status_and_retention_after_a_battle`
- `test_integration_battle.py::test_second_battle_starts_from_the_saved_mastery`
- `test_memory_model.py::test_update_sets_last_review`
- `test_memory_model.py::test_new_concept_is_displayed_at_fifty_percent`
- `test_memory_model.py::test_displayed_level_grows_with_theta`
- `test_models.py::test_default_mastery_is_a_blank_concept`
- `test_repository.py::test_never_reviewed_student_has_no_saved_mastery`
- `test_repository.py::test_mastery_without_review_date_is_kept_as_none`
- `test_repository.py::test_dashboard_rows_list_every_concept_of_the_student`
- `test_ui_acceptance.py::test_new_student_sees_every_concept_as_not_evaluated`
- `test_ui_acceptance.py::test_dashboard_and_progress_page_reflect_a_finished_battle`

### BF-09 Évolution de la maîtrise dans le temps
- `test_game_service.py::test_finishing_twice_records_the_battle_only_once`
- `test_game_service.py::test_progress_curve_gets_one_point_per_finished_battle`
- `test_repository.py::test_progress_history_lists_finished_battles_in_order`
- `test_ui_acceptance.py::test_dashboard_and_progress_page_reflect_a_finished_battle`
- `test_ui_acceptance.py::test_progress_page_is_empty_before_any_battle`

### BF-10 Importer une banque de questions
- `test_bootstrap.py::test_initialization_creates_accounts_and_question_bank`
- `test_bootstrap.py::test_bank_files_are_fully_valid`
- `test_bootstrap.py::test_csv_and_json_banks_contain_the_same_questions`
- `test_importer.py::test_valid_csv_is_imported`
- `test_importer.py::test_semicolon_separated_csv_is_accepted`
- `test_importer.py::test_csv_starting_with_a_bom_is_accepted`
- `test_importer.py::test_lowercase_answer_letter_and_uppercase_difficulty_are_accepted`
- `test_importer.py::test_invalid_line_is_rejected_with_its_number_and_valid_ones_are_kept`
- `test_importer.py::test_every_problem_of_a_line_is_reported`
- `test_importer.py::test_identical_options_are_rejected`
- `test_importer.py::test_empty_option_is_rejected`
- `test_importer.py::test_blank_lines_are_ignored`
- `test_importer.py::test_chapter_is_not_created_when_every_line_is_invalid`
- `test_importer.py::test_chapter_title_is_required`
- `test_importer.py::test_importing_the_same_file_twice_adds_nothing`
- `test_importer.py::test_valid_json_is_imported`
- `test_importer.py::test_json_item_with_wrong_number_of_options_is_rejected`
- `test_importer.py::test_decode_upload_handles_utf8_bom_and_excel_encoding`
- `test_importer.py::test_format_is_detected_from_the_file_name`
- `test_importer.py::test_unsupported_formats_are_refused`
- `test_importer.py::test_missing_concept_and_too_long_fields_are_rejected`
- `test_importer.py::test_line_with_only_separators_is_ignored`
- `test_importer.py::test_json_item_with_an_invalid_field_is_rejected_with_its_number`
- `test_models.py::test_question_rejects_unknown_difficulty`
- `test_models.py::test_question_rejects_out_of_range_answer`
- `test_repository.py::test_get_or_create_chapter_does_not_duplicate`
- `test_repository.py::test_duplicate_question_is_refused`
- `test_ui_acceptance.py::test_the_administrator_can_open_the_import_screen`

### BF-11 Modifier ou supprimer des questions
_Aucun test automatisé (non réalisé)._

### BNF-01 Performance
- `test_integration_battle.py::test_next_question_is_fast_with_1000_questions`

### BNF-02 Sécurité
- `test_auth.py::test_hash_has_expected_format_and_hides_the_password`
- `test_auth.py::test_same_password_gives_different_hashes_thanks_to_salt`
- `test_auth.py::test_production_iteration_count_is_strong`
- `test_auth.py::test_register_never_stores_the_password_in_clear`
- `test_auth.py::test_student_is_refused_admin_actions`
- `test_auth.py::test_nobody_logged_in_is_refused_admin_actions`
- `test_auth.py::test_admin_passes_the_admin_check`
- `test_bootstrap.py::test_initialization_does_not_overwrite_existing_passwords`
- `test_importer.py::test_student_cannot_import_questions`
- `test_importer.py::test_anonymous_visitor_cannot_import_questions`
- `test_repository.py::test_unknown_role_is_refused_by_the_database`
- `test_repository.py::test_sql_injection_attempt_is_harmless`
- `test_ui_acceptance.py::test_import_menu_is_only_visible_to_the_administrator`
- `test_ui_acceptance.py::test_a_student_who_reaches_the_import_screen_is_refused`

### BNF-03 Usabilité
_Aucun test automatisé (test manuel)._

### BNF-04 Fiabilité
- `test_bootstrap.py::test_initialization_can_be_run_again_without_duplicates`
- `test_bootstrap.py::test_unreadable_bank_stops_the_initialization_with_a_clear_error`
- `test_game_service.py::test_second_battle_continues_from_saved_mastery`
- `test_game_service.py::test_failed_save_ignores_the_answer_and_lets_the_student_retry`
- `test_importer.py::test_short_line_is_rejected_without_crashing`
- `test_importer.py::test_missing_columns_reject_the_whole_file`
- `test_importer.py::test_empty_file_is_refused_with_a_message`
- `test_importer.py::test_binary_garbage_does_not_crash`
- `test_importer.py::test_json_item_that_is_not_an_object_is_rejected`
- `test_importer.py::test_invalid_json_syntax_is_refused_with_a_message`
- `test_importer.py::test_json_that_is_not_a_list_is_refused`
- `test_importer.py::test_empty_json_list_is_refused`
- `test_importer.py::test_oversized_csv_cell_does_not_crash`
- `test_integration_battle.py::test_a_perfect_player_wins_and_everything_is_saved`
- `test_repository.py::test_invalid_data_is_refused_by_the_database_without_leftovers`
- `test_repository.py::test_mastery_round_trip`
- `test_repository.py::test_progress_survives_an_application_restart`
- `test_repository.py::test_init_db_can_be_run_twice`
- `test_repository.py::test_answer_and_mastery_are_saved_together_or_not_at_all`

### BNF-05 Maintenabilité
- `test_architecture.py::test_ui_files_never_touch_the_database`
- `test_architecture.py::test_logic_and_data_layers_do_not_depend_on_the_interface`
- `test_architecture.py::test_game_rules_live_in_the_logic_layer_only`
- `test_architecture.py::test_every_public_function_and_class_has_a_docstring`
- `test_traceability.py::test_every_automated_requirement_has_at_least_one_test`
- `test_traceability.py::test_tests_only_cite_requirements_that_exist`
- `test_traceability.py::test_manual_and_unimplemented_requirements_are_declared_as_such`
- `test_traceability.py::test_generated_matrix_files_are_up_to_date`

### BNF-06 Portabilité
_Aucun test automatisé (test manuel)._

### BNF-07 Disponibilité
_Aucun test automatisé (test manuel)._

### BNF-08 Exactitude du modèle d'adaptation
- `test_game_service.py::test_retention_drops_as_days_go_by`
- `test_memory_model.py::test_recall_is_one_right_after_review`
- `test_memory_model.py::test_recall_decreases_with_time`
- `test_memory_model.py::test_recall_matches_formula`
- `test_memory_model.py::test_higher_stability_means_slower_forgetting`
- `test_memory_model.py::test_correct_answer_raises_level_and_stability`
- `test_memory_model.py::test_wrong_answer_lowers_level_and_halves_stability`
- `test_memory_model.py::test_stability_never_goes_below_minimum`
- `test_memory_model.py::test_repeated_success_makes_forgetting_slower`
