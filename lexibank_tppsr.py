from collections import defaultdict

import attr
from pathlib import Path
from pylexibank import Concept, Language, FormSpec, Lexeme
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import progressbar

from csvw.metadata import URITemplate

from lingpy import prosodic_string
from clldutils.misc import slug

@attr.s
class CustomConcept(Concept):
    French_Gloss = attr.ib(default=None)
    Latin_Gloss = attr.ib(default=None)
    Number = attr.ib(default=None)


@attr.s
class CustomLanguage(Language):
    Number = attr.ib(default=None)
    Canton = attr.ib(default=None)
    Glottocode = attr.ib(default="stan1290")
    Family = attr.ib(default="Indo-European")
    DialectGroup = attr.ib(default=None)
    YearOfRecording = attr.ib(default=None)
    Population = attr.ib(default=None)
    SpeakerAge = attr.ib(default=None)
    SpeakerProficiency = attr.ib(default=None)
    SpeakerLanguageUse = attr.ib(default=None)
    SpeakerGender = attr.ib(default=None)


@attr.s
class CustomLexeme(Lexeme):
    Scan = attr.ib(default=None)
    ProsodicStructure = attr.ib(default=None)
    SegmentedValue = attr.ib(default=None)


class Dataset(BaseDataset):
    id = "tppsr"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage
    lexeme_class = CustomLexeme
    form_spec = FormSpec(first_form_only=True, missing_data=("#NAME?", ))

    def cmd_makecldf(self, args):
        args.writer.add_sources()

        # We can link forms to scans of the page in the source where they appear:
        args.writer.cldf["FormTable", "Scan"].valueUrl = URITemplate(
            'https://ia801505.us.archive.org/BookReader/BookReaderImages.php'
            '?zip=/28/items/gauchat-et-al-1925-tppsr/gauchat-et-al-1925-tppsr_jp2.zip'
            '&file=gauchat-et-al-1925-tppsr_jp2/gauchat-et-al-1925-tppsr_{Scan}.jp2'
            '&id=Z2F1Y2hhdC1ldC1hbC0xOTI1LXRwcHNy&scale=5')
        for c in ['YearOfRecording', 'Population', 'SpeakerAge']:
            args.writer.cldf['LanguageTable', c].datatype.base = 'integer'
            args.writer.cldf['LanguageTable', c].datatype.minimum = 0

        values = self.raw_dir.read_csv('tppsr-db-v20.txt', delimiter='\t')
        forms = self.raw_dir.read_csv('tppsr-db-v20-ipa-narrow.txt', delimiter='\t')

        concepts = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = '{0}_{1}'.format(concept.id, slug(concept.attributes['french']))
            args.writer.add_concept(
                ID=idx,
                Number=concept.number,
                Name=concept.english,
                French_Gloss=concept.attributes['french'],
                Latin_Gloss=concept.attributes['latin'],
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss
            )
            concepts[concept.number] = (
                idx,
                concept.attributes['page'],
                concept.attributes['french']
            )
            
        languages = args.writer.add_languages(lookup_factory='Number')

        phrase_data = defaultdict(dict)
        for row1, row2 in progressbar(zip(values, forms), desc='cldfify'):
            entry = row1[2]
            for s, t in [('\u0320', '')]:
                entry = entry.replace(s, t)
            tokens = self.tokenizer({}, entry, column='IPA')
            page = int(concepts[row1[0]][1]) + (1 if int(row1[1]) > 31 else 0)

            if row1[2].replace('_', '').replace('-', '').strip():
                phrase_data[row1[1]][row1[0]] = (row2[2], row1[2])
                args.writer.add_form_with_segments(
                    Value=row1[2],
                    Form=''.join(tokens),
                    Segments=tokens,
                    Profile=' '.join(self.tokenizer({}, entry, column='Grapheme')),
                    Source=['Gauchat1925[{0}]'.format(page)],
                    Language_ID=languages[row1[1]],
                    Parameter_ID=concepts[row1[0]][0],
                    Scan=str(page+18).rjust(4, '0'),
                    ProsodicStructure=prosodic_string(tokens, _output='CcV'),
                    SegmentedValue=' '.join(self.tokenizer({}, entry, column='Graphemes'))
                )

        args.writer.cldf.add_component('ExampleTable', 'Alt_Transcription')

        for phrase in self.etc_dir.read_csv('phrases.csv', dicts=True):
            for lid, data in sorted(phrase_data.items(), key=lambda i: i[0]):
                lid = languages[lid]
                cids = phrase['Concepts'].split()
                try:
                    args.writer.objects['ExampleTable'].append(dict(
                        ID='{}-{}'.format(phrase['ID'], lid),
                        Language_ID=lid,
                        Primary_Text=' '.join([data[cid][0] for cid in cids]),
                        Translated_Text=' '.join([concepts[cid][2] for cid in cids]),
                        Alt_Transcription=' '.join([data[cid][1] for cid in cids]),
                    ))
                except KeyError:
                    pass
