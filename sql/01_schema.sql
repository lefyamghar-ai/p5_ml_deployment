-- Genere par : python scripts/create_db.py --dump-sql (ne pas modifier a la main)

CREATE TABLE employees (
	id_employee INTEGER NOT NULL, 
	annees_dans_l_entreprise SMALLINT NOT NULL, 
	annes_sous_responsable_actuel SMALLINT NOT NULL, 
	a_quitte_l_entreprise BOOLEAN NOT NULL, 
	age SMALLINT NOT NULL, 
	genre VARCHAR(1) NOT NULL, 
	revenu_mensuel INTEGER NOT NULL, 
	statut_marital VARCHAR(20) NOT NULL, 
	departement VARCHAR(30) NOT NULL, 
	poste VARCHAR(40) NOT NULL, 
	nombre_experiences_precedentes SMALLINT NOT NULL, 
	annee_experience_totale SMALLINT NOT NULL, 
	annees_dans_le_poste_actuel SMALLINT NOT NULL, 
	satisfaction_employee_environnement SMALLINT NOT NULL, 
	note_evaluation_precedente SMALLINT NOT NULL, 
	niveau_hierarchique_poste SMALLINT NOT NULL, 
	satisfaction_employee_nature_travail SMALLINT NOT NULL, 
	satisfaction_employee_equipe SMALLINT NOT NULL, 
	satisfaction_employee_equilibre_pro_perso SMALLINT NOT NULL, 
	note_evaluation_actuelle SMALLINT NOT NULL, 
	heure_supplementaires VARCHAR(3) NOT NULL, 
	augementation_salaire_precedente FLOAT NOT NULL, 
	nombre_participation_pee SMALLINT NOT NULL, 
	nb_formations_suivies SMALLINT NOT NULL, 
	distance_domicile_travail SMALLINT NOT NULL, 
	niveau_education SMALLINT NOT NULL, 
	domaine_etude VARCHAR(40) NOT NULL, 
	frequence_deplacement VARCHAR(20) NOT NULL, 
	annees_depuis_la_derniere_promotion SMALLINT NOT NULL, 
	PRIMARY KEY (id_employee), 
	CONSTRAINT ck_employees_age CHECK (age BETWEEN 18 AND 70), 
	CONSTRAINT ck_employees_revenu CHECK (revenu_mensuel > 0), 
	CONSTRAINT ck_employees_heures_sup CHECK (heure_supplementaires IN ('Oui', 'Non')), 
	CONSTRAINT ck_employees_satisfactions CHECK (satisfaction_employee_environnement BETWEEN 1 AND 4 AND satisfaction_employee_nature_travail BETWEEN 1 AND 4 AND satisfaction_employee_equipe BETWEEN 1 AND 4 AND satisfaction_employee_equilibre_pro_perso BETWEEN 1 AND 4)
);


CREATE TABLE prediction_inputs (
	id SERIAL NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	employee_id INTEGER, 
	age SMALLINT NOT NULL, 
	genre VARCHAR(1) NOT NULL, 
	revenu_mensuel INTEGER NOT NULL, 
	statut_marital VARCHAR(20) NOT NULL, 
	departement VARCHAR(30) NOT NULL, 
	poste VARCHAR(40) NOT NULL, 
	nombre_experiences_precedentes SMALLINT NOT NULL, 
	annee_experience_totale SMALLINT NOT NULL, 
	annees_dans_le_poste_actuel SMALLINT NOT NULL, 
	satisfaction_employee_environnement SMALLINT NOT NULL, 
	note_evaluation_precedente SMALLINT NOT NULL, 
	niveau_hierarchique_poste SMALLINT NOT NULL, 
	satisfaction_employee_nature_travail SMALLINT NOT NULL, 
	satisfaction_employee_equipe SMALLINT NOT NULL, 
	satisfaction_employee_equilibre_pro_perso SMALLINT NOT NULL, 
	note_evaluation_actuelle SMALLINT NOT NULL, 
	heure_supplementaires VARCHAR(3) NOT NULL, 
	augementation_salaire_precedente FLOAT NOT NULL, 
	nombre_participation_pee SMALLINT NOT NULL, 
	nb_formations_suivies SMALLINT NOT NULL, 
	distance_domicile_travail SMALLINT NOT NULL, 
	niveau_education SMALLINT NOT NULL, 
	domaine_etude VARCHAR(40) NOT NULL, 
	frequence_deplacement VARCHAR(20) NOT NULL, 
	annees_depuis_la_derniere_promotion SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_prediction_inputs_age CHECK (age BETWEEN 18 AND 70), 
	CONSTRAINT ck_prediction_inputs_revenu CHECK (revenu_mensuel > 0), 
	CONSTRAINT ck_prediction_inputs_heures_sup CHECK (heure_supplementaires IN ('Oui', 'Non')), 
	CONSTRAINT ck_prediction_inputs_satisfactions CHECK (satisfaction_employee_environnement BETWEEN 1 AND 4 AND satisfaction_employee_nature_travail BETWEEN 1 AND 4 AND satisfaction_employee_equipe BETWEEN 1 AND 4 AND satisfaction_employee_equilibre_pro_perso BETWEEN 1 AND 4), 
	FOREIGN KEY(employee_id) REFERENCES employees (id_employee)
);

CREATE INDEX ix_prediction_inputs_employee_id ON prediction_inputs (employee_id);
CREATE INDEX ix_prediction_inputs_created_at ON prediction_inputs (created_at);

CREATE TABLE predictions (
	id SERIAL NOT NULL, 
	input_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	probabilite_depart FLOAT NOT NULL, 
	prediction SMALLINT NOT NULL, 
	seuil FLOAT NOT NULL, 
	model_version VARCHAR(20) NOT NULL, 
	latency_ms FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_predictions_probabilite CHECK (probabilite_depart BETWEEN 0 AND 1), 
	CONSTRAINT ck_predictions_prediction CHECK (prediction IN (0, 1)), 
	UNIQUE (input_id), 
	FOREIGN KEY(input_id) REFERENCES prediction_inputs (id) ON DELETE CASCADE
);

CREATE INDEX ix_predictions_created_at ON predictions (created_at);

GRANT USAGE ON SCHEMA public TO technova_app;
GRANT SELECT ON employees TO technova_app;
GRANT SELECT, INSERT ON prediction_inputs, predictions TO technova_app;
GRANT USAGE ON SEQUENCE prediction_inputs_id_seq, predictions_id_seq TO technova_app;
