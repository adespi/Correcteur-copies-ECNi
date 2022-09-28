from fcntl import F_SEAL_SEAL
from platform import java_ver
from pdf2image import convert_from_path
from PIL import Image
import numpy  as np
import os
from PyPDF2 import PdfFileWriter, PdfFileReader
import natsort
import re
import shutil
import pandas as pd

"""
FONCTIONEMENT :
- Corriger les erreurs de frappe dans les inputs
- Convertir le pdf en images
- Trouver les cases dans la page (elles sont toutes dans la meme colonne et ont toutes la meme couleur)
- Verifier si la case est cochée ou non
- Appareiller les items de la copie avec les items du sujet de reference (les items sont dans un ordre aléatoire dans toutes les copies pour éviter la triche)
- Enregistrer les notes et les réponses dans des fichiers
"""

def pdf_to_png(file_name):
    inputpdf = PdfFileReader(open(file_name, "rb"))
    file_name = os.path.splitext(file_name)[0]
    for i in range(inputpdf.numPages):
        output = PdfFileWriter()
        output.addPage(inputpdf.getPage(i))
        with open("temp/page%s.pdf" % i, "wb") as outputStream:
            output.write(outputStream)
        pages = convert_from_path("temp/page%s.pdf" % i, 500)
        pages[0].save("temp/page%s.png" % str(i).zfill(3), 'PNG')
        os.remove("temp/page%s.pdf" % i)

def extract_one_page(file_name):
    img = Image.open(file_name)
    image_data = np.asarray(img)
    
    responses = np.empty(0)
    while (True):
        try:
            positions = np.where(image_data[:,254,0]==64)[0]
            position = positions[0]+35
        except:
            break
        try:
            if positions[0] == positions[1] - 1 == positions[2] - 2 == positions[3] - 3:
                responses = np.append(responses, image_data[position,272,0])
                image_data = image_data[position+100:]
            else :
                image_data = image_data[positions[0]+1:]
        except:
            image_data = image_data[positions[0]+1:]

    return responses==0


def extract_one_pdf_answers(file_name):
    responses = np.empty(0)
    if len(os.listdir('temp/')) != 0:
        raise Exception("Le dossier temp n'est pas vide") 
    pdf_to_png(file_name)
    for image_file in natsort.natsorted(os.listdir("temp")):
        responses = np.append(responses, extract_one_page("temp/"+image_file))
        os.remove("temp/"+image_file)
    return responses


def extract_items(file_name):
    pdfFileObj = open(file_name, 'rb')
    pdfReader = PdfFileReader(pdfFileObj) 
    print(pdfReader.numPages, file_name)
    text_extracted = ""
    for i in range(pdfReader.numPages):
        pageObj = pdfReader.getPage(i)
        text_extracted += pageObj.extractText()
    pdfFileObj.close()

    text_extracted = text_extracted.replace("\n","")
    list_items_extracted=[]
    fini = False
    while not fini :
        for n in range(5):
            item_letters = ["A","B","C","D","E"]

            locations = [text_extracted.find("Proposition %s" % item_letters[n]), text_extracted.find("Proposition %s" % item_letters[(n+1)%5]),re.search("Epreuve (DCP|QI|LCA)", text_extracted).span()[0] if re.search("Epreuve (DCP|QI|LCA)", text_extracted) is not None else -1]
            text_extracted=text_extracted[locations[0]:]

            locations = [text_extracted.find("Proposition %s" % item_letters[n]), text_extracted.find("Proposition %s" % item_letters[(n+1)%5]),re.search("Epreuve (DCP|QI|LCA)", text_extracted).span()[0] if re.search("Epreuve (DCP|QI|LCA)", text_extracted) is not None else -1]
            try:
                re_out = re.search("^Proposition [A-Z]Epreuve [A-Z]{2,3}.{1,38}/[0-9]{1,3}", text_extracted)
                re_out.span()[0]
                locations[0] = re_out.span()[1]-13
                locations[2] = locations[1]

            except:
                "f"

            if locations[1]== -1:
                fini = True
                locations[1]=locations[2]
            elif locations[2] > locations[0] :
                locations[1] = min(locations[1], locations[2])
            list_items_extracted.append(text_extracted[locations[0]+13:locations[1]])
            text_extracted=text_extracted[locations[0]+1:]
     
    return(list_items_extracted)

def match_response(sujet,copie):
    items_sujet = extract_items(sujet)
    items_copie = extract_items(copie)
    correspondance = []
    for x in items_sujet:
        position = items_copie.index(x)
        items_copie[position] = ""
        correspondance.append(position)

    return correspondance

nombre_de_questions_DP = [14,14,15,13,13,14,
                            15,17,15,14,15,15,
                            16,15,14,14,13,15]
nombre_de_questions_QI = 120
nombre_de_questions_LCA = [16,16]

def extract_one_person(student_id):
    reponses_DP = []
    reponses_QI = []
    reponses_LCA = []

    for i in range(3):
        correspondance = match_response("in/sujet/DCP%s ECN 2022.pdf" % str(i+1),"in/copie/%s/DCP%s ECN 2022.pdf" % (student_id,str(i+1)))
        answers = extract_one_pdf_answers("in/copie/%s/DCP%s ECN 2022.pdf" % (student_id,str(i+1)))
        answers = answers[[correspondance]][0]
        answers = np.split(answers,sum(nombre_de_questions_DP[i*6:i*6+6]))
        first = 0
        last = 0
        for x in range(6):
            last += nombre_de_questions_DP[6*i+x]
            reponses_DP.append(answers[first:last])
            first += nombre_de_questions_DP[6*i+x]
    correspondance = match_response("in/sujet/QI ECN 2022.pdf", "in/copie/%s/QI ECN 2022.pdf" % student_id)
    answers = extract_one_pdf_answers("in/copie/%s/QI ECN 2022.pdf" % student_id)
    answers = answers[[correspondance]][0]
    answers = np.split(answers,nombre_de_questions_QI)
    reponses_QI.append(answers)

    correspondance = match_response("in/sujet/LCA ECN 2022.pdf", "in/copie/%s/LCA ECN 2022.pdf" % student_id)
    answers = extract_one_pdf_answers("in/copie/%s/LCA ECN 2022.pdf" % student_id)
    answers = answers[[correspondance]][0]
    answers = np.split(answers,sum(nombre_de_questions_LCA))
    first = 0
    last = 0
    for x in range(2):
        last += nombre_de_questions_LCA[x]
        reponses_LCA.append(answers[first:last])
        first += nombre_de_questions_LCA[x]

    return [reponses_DP, reponses_QI, reponses_LCA]


if not os.path.exists("in/copie/"):
    os.mkdir("in/copie/")
if not os.path.exists("temp/"):
    os.mkdir("temp/")
if not os.path.exists("out/"):
    os.mkdir("out/")

for x in [["1 (DCP1)",'DCP1 ECN 2022.pdf'],["2 (QI)",'QI ECN 2022.pdf'],["3 (DCP2)",'DCP2 ECN 2022.pdf'],["4 (LCA)",'LCA ECN 2022.pdf'],["5 (DCP3)",'DCP3 ECN 2022.pdf']]:
    search_dir = "in/Copie ECNi (File responses)/Copie Epreuve %s (File responses)/" % x[0]

    files = os.listdir(search_dir)
    files = [os.path.join(search_dir, f) for f in files] # add path to each file
    files.sort(key=lambda y: os.path.getmtime(y))
    i = 0
    for file in files :
        out_folder = "in/copie/copie_%s/" % i
        if not os.path.exists(out_folder):
            os.mkdir(out_folder)
        source = file
        'in/Copie ECNi (File responses)/Copie Epreuve 1 (File responses)/epreuve1 - Antoine Despinasse.pdf'
        destination = out_folder + x[1]
        shutil.copy(source, destination)
        'in/copie/TEST/DCP1 ECN 2022.pdf'
        i += 1


fin = open("in/Copie ECNi.csv", "rt")
#output file to write the result to
fout = open("in/Copie ECNi_t.csv", "wt")
#for each line in the input file
for line in fin:
    #read replace the string and write to output file
    to_replace = []
    a= '"378","382","378"'
    b= '"378","382.94","378"'
    to_replace.append([a,b])
    a= '"345","313,3","313,6"'
    b= '"345","313,6","313,6"'
    to_replace.append([a,b])
    a= '360","332,2","294","341,25","310,8","360","360","329,54","305,2","378","401,63","1623, 6","8284,86"'
    b= '360","333,2","294","341,25","310,8","360","306","329,54","305,2","378","401,63","1623,6","8284,86"'
    to_replace.append([a,b])
    a= '"371,25","1625,4","8049,47"'
    b= '"371,25","1625,4","8409,47"'
    to_replace.append([a,b])

    a= '"455,63","1848,6","922,61"'
    b= '"455,63","1848,6","9200,61"'
    to_replace.append([a,b])
    a= ''
    b= ''
    #to_replace.append([a,b])
    a= ''
    b= ''
    #to_replace.append([a,b])
    a= ''
    b= ''
    #to_replace.append([a,b])

    a= '","'
    b= '"\t"'
    to_replace.append([a,b])
    a= ','
    b= '.'
    to_replace.append([a,b])
    a= '"2022/07/18 12:24:45 PM UTC+2"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"Cf"\t"ht'
    b= '"2022/07/18 12:24:45 PM UTC+2"\t"240"\t"315"\t"302.84"\t"339.23"\t"200.31"\t"300"\t"291.2"\t"313.76"\t"338.8"\t"321"\t"271.6"\t"232.4"\t"241.5"\t"240.8"\t"246"\t"156"\t"303.69"\t"266"\t"479.25"\t"435.38"\t"1294.2"\t"7128.96"\t"ht'
    to_replace.append([a,b])
    a= '"345.69"\t"350"\t"418.5"\t"401.63"\t"1679.4"\t"8602.2"\t"'
    b= '"345.69"\t"350"\t"418.5"\t"401.63"\t"1679.4"\t"8606.2"\t"'
    to_replace.append([a,b])
    a= '"323"\t"355.38"\t"282"\t"291.2"\t"345.88"\t"313.6"\t"237"\t"355.6"\t"285.6"\t"313.88"\t"277.2"\t"366"\t"291"\t"297.23"\t"319.2"\t"313.88"\t"300.38"\t"1587.6"\t"7892.24"'
    b= '"323.08"\t"355.38"\t"282"\t"291.2"\t"345.88"\t"313.6"\t"237"\t"355.6"\t"285.6"\t"359.63"\t"277.2"\t"366"\t"291"\t"297.23"\t"319.2"\t"313.88"\t"300.38"\t"1587.6"\t"7892.24"'
    to_replace.append([a,b])
    a= ' "'
    b= '"'
    to_replace.append([a,b])
    a= '" '
    b= '"'
    to_replace.append([a,b])
    a= '. '
    b= ''
    to_replace.append([a,b])
    for x in to_replace:  #si erreurs a corriger
        line = line.replace(x[0],x[1])
    fout.write(line)

#close input and output files
fin.close()
fout.close()

notes = pd.read_csv('in/Copie ECNi_t.csv',  delimiter='\t').to_numpy()

for person in os.listdir('in/copie'):
    print(person)
    
    if not os.path.exists('out/copie_%s.npy' % person):
        copie_one_person =extract_one_person(person)
        with open('out/copie_%s.npy' % person, 'wb') as f:
            np.save(f, copie_one_person)
    
    if not os.path.exists('out/notes_%s.npy' % person):
        i=int(person[6:])
        notes_one_person = notes[i][1:23]
        print(notes_one_person, sum(notes_one_person[:-1]), abs(sum(notes_one_person[:-1]) - notes_one_person[-1]))
        if abs(sum(notes_one_person[:-1]) - notes_one_person[-1]) > 0.04:
            raise Exception("La note totale ne correspond pas à la somme des notes")
        with open('out/notes_%s.npy' % person, 'wb') as f:
            np.save(f, notes_one_person)
