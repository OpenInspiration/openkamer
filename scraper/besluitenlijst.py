import re
from io import StringIO

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

# TODO: compile regex in this module to improve performance


class BesluitenLijst(object):
    def __init__(self, text):
        self.text = text
        self.title = self.get_title(text)
        self.voortouwcommissie = self.get_voortouwcommissie(text)
        self.activiteitnummer = self.get_activiteitnummer(text)
        self.url = ''
        self.date_published = None
        self.items = create_besluit_items(text)

    def __str__(self):
        return self.title + '\n' + self.voortouwcommissie + '\n' + self.activiteitnummer

    @staticmethod
    def get_title(text):
        pattern = 'Document:\s+(.*)'
        titles = re.findall(
            pattern=pattern,
            string=text
        )
        return titles[0]

    @staticmethod
    def get_voortouwcommissie(text):
        pattern = 'Voortouwcommissie:\s+(.*)'
        titles = re.findall(
            pattern=pattern,
            string=text
        )
        return titles[0]

    @staticmethod
    def get_activiteitnummer(text):
        pattern = 'Activiteitnummer:\s+(.*)'
        titles = re.findall(
            pattern=pattern,
            string=text
        )
        return titles[0]


class BesluitItem(object):
    def __init__(self):
        self.title = ''
        self.cases = []

    def print(self):
        print('Agendapunt: ' + self.title)
        for case in self.cases:
            print('------------')
            case.print()


class BesluitItemCase(object):
    def __init__(self, title):
        self.title = title
        self.related_document_ids = self.get_related_document_ids(title)
        self.decisions = []
        self.notes = []
        self.extra = ''
        self.volgcommissies = []

    @staticmethod
    def get_related_document_ids(text):
        pattern = "[0-9]{5}-[0-9]{1,2}"
        document_ids = re.findall(pattern, text)
        return document_ids

    def print(self):
        print('Zaak: ' + self.title)
        print('decisions:')
        print(self.decisions)
        print('notes:')
        print(self.notes)
        print('volgcommissies:')
        print(self.volgcommissies)
        print('related documents:')
        print(self.related_document_ids)


def create_besluit_items(text):
    punten = find_agendapunten(text)
    besluit_items = []
    for punt in punten:
        besluit = BesluitItem()
        besluit.title = punt['title']
        besluit_text = text[punt['start']:punt['end']]
        cases = find_cases(besluit_text)
        for case in cases:
            item_case = BesluitItemCase(case['title'])
            case_text = besluit_text[case['start']:case['end']]
            decisions = find_decisions(case_text)
            for decision in decisions:
                item_case.decisions.append(decision['title'])
            notes = find_notes(case_text)
            for note in notes:
                item_case.notes.append(note['title'])
            volgcommissies = find_volgcommissies(case_text)
            for volgcommissie in volgcommissies:
                item_case.volgcommissies.append(volgcommissie['title'])
            besluit.cases.append(item_case)
        # besluit.print()
        besluit_items.append(besluit)
    return besluit_items


def besluitenlijst_pdf_to_text(filepath):
    text = pdf_to_text(filepath)
    text = format_text(text)
    # with open('data/lijst.txt', 'w') as fileout:
    #     fileout.write(text)
    return text


def create_besluitenlijst(text):
    obj = BesluitenLijst(text)
    return obj


def find_agendapunten(text):
    pattern = "\d+\.\s+Agendapunt:(.*)"
    return find_items(pattern, text)


def find_cases(text):
    pattern = "Zaak:\s+(.*)"
    return find_items(pattern, text)


def find_decisions(text):
    pattern = "Besluit:(.*)"
    return find_items(pattern, text)


def find_notes(text):
    pattern = "Noot:(.*)"
    return find_items(pattern, text)


def find_volgcommissies(text):
    pattern = "Volgcommissie\(s\):(.*)"
    return find_items(pattern, text)


def find_items(pattern, text):
    matches = re.finditer(
        pattern=pattern,
        string=text
    )
    items = []
    matches = list(matches)
    for index, obj in enumerate(matches):
        if index < (len(matches)-1):
            end = matches[index+1].span()[0]
        else:
            end = len(text)
        item ={
            'title': obj.group(1).strip(),
            'start': obj.span()[0],
            'end': end
        }
        items.append(item)
    return items


def pdf_to_text(filepath):
    # based on http://stackoverflow.com/a/26495057/607041
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    # laparams = LAParams()
    laparams = None
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    with open(filepath, 'rb') as filein:
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        password = ""
        maxpages = 0
        caching = True
        pagenos=set()
        for page in PDFPage.get_pages(filein, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
            interpreter.process_page(page)
        text = retstr.getvalue()
        device.close()
        retstr.close()
    return text


def format_text(text):
    text = format_whitespaces(text)
    text = format_agendapunten(text)
    text = add_line_before('Zaak:', text)
    text = add_line_before('Besluit:', text)
    text = add_line_before('Noot:', text)
    text = add_line_before('Volgcommissie\(s\):', text)
    text = add_line_before('Griffier:', text)
    text = add_line_before('Activiteitnummer:', text)
    text = remove_page_numbers(text)
    return text


def format_whitespaces(text):
    pattern = "\s{4,}"
    result = re.sub(
        pattern=pattern,
        repl='\n\n',
        string=text
    )
    return result


def format_agendapunten(text):
    pattern = "\d+\.\s+Agendapunt:"
    result = re.sub(
        pattern=pattern,
        repl=add_double_new_line,
        string=text
    )
    return result


def remove_page_numbers(text):
    pattern = r'\n\s+\d+\s+\n'
    result = re.sub(
        pattern=pattern,
        repl='\n\n',
        string=text
    )
    return result


def add_line_before(pattern, text):
    result = re.sub(
        pattern=pattern,
        repl=add_new_line,
        string=text
    )
    return result


def add_new_line(matchobj):
    return '\n' + matchobj.group(0)


def add_double_new_line(matchobj):
    return '\n\n' + matchobj.group(0)