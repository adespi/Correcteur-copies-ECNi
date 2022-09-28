import os
import numpy as np
import random
import itertools

"""
FONCTIONNEMENT :
- Importer les fichiers generes par "extract_copie.py"
- Pour chaque epreuve, essayer 10 fois de :
    - Generer une correction aleatoire
    - Essayer en boucle jusqu'a bloquer :
        - Essayer de la modifier la correction generee
        - Si la modification rapproche les notes calculees des notes reelles, garder la modification
    - Si les notes calculees et les notes reelles sont le meme, enregistrer la correction

"""

def calculate_difference_one(copie, note, best_guess, points_par_qcm, coef_qcm):
    note_calculated = 0
    for qcm in range(len(copie)):
        discordances = 0
        for item in range(5):
            if best_guess[qcm][item]<2:
                if copie[qcm][item] != best_guess[qcm][item]:
                    discordances += 1
            else :
                if copie[qcm][item] != (best_guess[qcm][item] -2):
                    discordances += 5
        if discordances == 0:
            note_calculated += 1 * coef_qcm[qcm]
        elif discordances == 1:
            note_calculated += 0.5 * coef_qcm[qcm]
        elif discordances == 2:
            note_calculated += 0.2 * coef_qcm[qcm]

    return abs(round(note_calculated*points_par_qcm,2)-note)


def calculate_difference_all(copies, notes, session_type, epreuve_number, best_guess, points_par_qcm, coef_qcm = None):
    if type(coef_qcm) == type(None):
        coef_qcm = np.ones(len(copies[0][session_type][epreuve_number]))
    difference=0.0
    differences=[]
    for x in range(len(copies)):
        note_number = epreuve_number
        if session_type == 1 :
            note_number += (18 + 2)
        elif session_type == 2 :
            note_number += 18
        difference+=calculate_difference_one(copies[x][session_type][epreuve_number], notes[x][note_number],best_guess,points_par_qcm, coef_qcm)
        #differences.append(calculate_difference_one(copies[x][session_type][epreuve_number], notes[x][note_number],best_guess,points_par_qcm, coef_qcm)) #TODO remove/add again if want print
    return difference, differences


def generate_new_guesses(best_guess, z_range):
    num_qcm=len(best_guess)
    new_guesses = []
    for x in random.sample(range(0, num_qcm), num_qcm):
        #for y in range(5):
        for y in random.sample(range(0, 5), 5):
            for z in range(z_range):
                if not best_guess[x,y]==z:
                    new_guess=best_guess.copy()
                    new_guess[x,y]=z
                    new_guesses.append(new_guess)
    return new_guesses

def calculate_correction_one_note_short(copies, notes, session_type, epreuve_number, points_par_qcm, nbr_qcm_coef_expected):
    num_qcm = len(copies[0][session_type][epreuve_number])
    best_guess=(np.random.rand(num_qcm,5)>0.5).astype(int) #0 = faux, 1 = vrai, 2 = MZ , 3 = PMZ

    best_score, differences=calculate_difference_all(copies, notes, session_type, epreuve_number, best_guess, points_par_qcm) #0 is best, absolute difference, no negative 
    saved_best = best_guess.copy()
    z_range = 2
    nbr_stall = 0
    coef_qcm = np.ones(len(copies[0][session_type][epreuve_number]))
    while True :
        print(np.round(np.asarray(differences)/points_par_qcm,3))
        print(coef_qcm)
        for new_guess in generate_new_guesses(best_guess, z_range):
            new_score, differences=calculate_difference_all(copies, notes, session_type, epreuve_number, new_guess, points_par_qcm, coef_qcm)
            if new_score < best_score :  
                best_guess = new_guess.copy()
                best_score = new_score
                nbr_stall = 0
                break

        print(z_range, nbr_stall, best_score)

        if (best_guess==saved_best).all():
            nbr_stall+=1
            if nbr_stall == 2:
                if z_range == 2 :
                    z_range = 4
                    print("enable PMZ/MZ")
                    nbr_stall = 0
                else :
                    break
        else:
            saved_best=best_guess.copy()
        

        if best_score < 1: #TODO change trigger
            break
    return best_guess, best_score


def import_copies_and_notes():
    copies, notes = [],[]
    for x in range(int(len(os.listdir('out'))/2)):
        with open('out/copie_copie_%s.npy' % x, 'rb') as f:
            copie_one_person = np.load(f,allow_pickle=True) #[DP[1,2,3,],QI[],LCA[1,2]]
            copies.append(copie_one_person)
        with open('out/notes_copie_%s.npy' % x, 'rb') as f:
            notes_one_person = np.load(f,allow_pickle=True) #[DP1,DP2,DPX,LCA1,LCA2,QI]
            notes.append(notes_one_person)
    return copies, notes


def all_sessions(copies, notes):
    best_guesses = []
    best_scores = []
    for session_type in range(3):
        for epreuve_number in range([18,1,2][session_type]):
            if os.path.exists('correction/Session %s Epreuve %s.npy' % (["DP","QI","LCA"][session_type], epreuve_number+1)):
                continue
            print("Session %s Epreuve %s" % (session_type, epreuve_number))
            if session_type == 0 :
                nbr_qcm_coef_expected =   [14,14,19,13,13,14,
                            15,17,15,14,15,15,
                            16,15,14,14,13,15][epreuve_number] #not nbr qcm reel mais nbr de qcm attendus en fonction des notes des personnes
                points_par_qcm = 420/nbr_qcm_coef_expected
            elif session_type == 1 :
                nbr_qcm_coef_expected = 120
                points_par_qcm = 18
            elif session_type == 2 :
                nbr_qcm_coef_expected = [16,16][epreuve_number]
                points_par_qcm = 540/nbr_qcm_coef_expected
            note_number = epreuve_number
            if session_type == 1 :
                note_number += (18 + 2)
            elif session_type == 2 :
                note_number += 18
            best_guess_multiple_tries=[]
            best_score_multiple_tries=[]
            for x in range(10):
                best_guess, best_score = calculate_correction_one_note_short(copies, notes, session_type, epreuve_number,points_par_qcm, nbr_qcm_coef_expected)
                best_guess_multiple_tries.append(best_guess)
                best_score_multiple_tries.append(best_score)
                if best_score<1:
                    break

            min_score_index = best_score_multiple_tries.index(min(best_score_multiple_tries))
            print (min_score_index,best_score_multiple_tries[min_score_index], best_score_multiple_tries)
            if best_score_multiple_tries[min_score_index] < 1 :
                print("SSSAAAVVVVEEEE")
                if not os.path.exists('correction/Session %s Epreuve %s.npy' % (["DP","QI","LCA"][session_type], epreuve_number+1)):
                    with open('correction/Session %s Epreuve %s.npy' % (["DP","QI","LCA"][session_type], epreuve_number+1), 'wb') as f:
                        np.save(f, best_guess_multiple_tries[min_score_index])
                    np.savetxt('correction/Session %s Epreuve %s.txt' % (["DP","QI","LCA"][session_type], epreuve_number+1),best_guess_multiple_tries[min_score_index],fmt='%d',delimiter='\t',newline='\n')
            best_guesses.append(best_guess_multiple_tries[min_score_index])
            best_scores.append(best_score_multiple_tries[min_score_index])
    return best_guesses, best_scores


copies, notes = import_copies_and_notes()

if not os.path.exists("correction/"):
    os.mkdir("correction/")

best_guesses, best_scores = all_sessions(copies, notes)
#print(all_sessions(copies, notes))