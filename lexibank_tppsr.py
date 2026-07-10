import re
import collections
import dataclasses
from typing import Optional
from pathlib import Path

from pylexibank import Concept, Language, FormSpec, Lexeme
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import progressbar
from csvw.metadata import URITemplate

from lingpy import prosodic_string
from clldutils.misc import slug

MEDIA_DOI = "10.5281/zenodo.21292636"
MEDIA_ZIP_URL = "https://zenodo.org/records/21292636/files/tppsr-scans.zip"


@dataclasses.dataclass
class CustomConcept(Concept):
    """TPPSR concepts are glossed in French and Latin as well."""
    French_Gloss: Optional[str] = None
    Latin_Gloss: Optional[str] = None
    Number: Optional[str] = None


@dataclasses.dataclass
class CustomLanguage(Language):
    """
    TPPSR Varieties are 'doculects', i.e. language varieties as documented at a particular point
    in time and space.
    """
    FullName: Optional[str] = None
    Number: Optional[str] = None
    Canton: Optional[str] = None
    Glottocode: str = "stan1290"
    Family: str = "Indo-European"
    DialectGroup: Optional[str] = None
    DateOfRecording: Optional[str] = None
    Population: Optional[str] = None
    SpeakerAge: Optional[str] = None
    SpeakerProficiency: Optional[str] = None
    SpeakerLanguageUse: Optional[str] = None
    SpeakerGender: Optional[str] = None
    Investigators: Optional[str] = None


@dataclasses.dataclass
class CustomLexeme(Lexeme):
    """TPPSR lexemes are digitized using scans of the original book pages."""
    Scan: Optional[str] = dataclasses.field(
        default=None,
        metadata={'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#mediaReference'})
    ProsodicStructure: Optional[str] = None
    SegmentedValue: Optional[str] = None


class Dataset(BaseDataset):
    id = "tppsr"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage
    lexeme_class = CustomLexeme
    form_spec = FormSpec(
        first_form_only=True, missing_data=("#NAME?", ),
        replacements=[("- - ", "-"), (" - ", "-"), ("- ", "-"), (" -", "")]
    )

    def cmd_makecldf(self, args):
        from pycldf import Dataset
        args.writer.add_sources()
        t = args.writer.cldf.add_component('MediaTable')
        t.common_props['dc:description'] = \
            ("This dataset links individual forms to the scan of the page in the original source "
             "it appears on. The scans have been obtained from the Public Domain data at "
             "https://archive.org/details/gauchat-et-al-1925-tppsr")
        # We add another URL for the scans. Note that the row URL discovery algorithm implemented
        # in pycldf will prefer the URL in the Download_URL column over this one.
        args.writer.cldf["MediaTable", "ID"].valueUrl = URITemplate(
            'https://https://s3.nexus.mpcdf.mpg.de/eva-dlce-tppsr/{Path_In_Zip}')

        for c in ['Population', 'SpeakerAge']:
            args.writer.cldf['LanguageTable', c].datatype.base = 'integer'
            args.writer.cldf['LanguageTable', c].datatype.minimum = 0

        for objid, o in self.raw_dir.read_json('tppsr_scans.json').items():
            num = re.search(
                r'tppsr_(?P<number>[0-9]{4})\.png', o['metadata']['path']).group('number')
            args.writer.objects['MediaTable'].append(dict(
                ID=num,
                Name=o['metadata']['path'],
                Description='Scan of ',
                Media_Type='image/png',
                Download_URL=MEDIA_ZIP_URL,
                Path_In_Zip=f"{objid}_{o['metadata']['path']}",
            ))

        values = self.raw_dir.read_csv('tppsr-db-v20.txt', delimiter='\t')
        forms = self.raw_dir.read_csv('tppsr-db-v20-ipa-narrow.txt', delimiter='\t')

        concepts = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = f"{concept.id}_{slug(concept.attributes['french'])}"
            args.writer.add_concept(
                ID=idx,
                Number=concept.number,
                Name=concept.gloss,
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

        phrase_data = collections.defaultdict(dict)
        for row1, row2 in progressbar(zip(values, forms), desc='cldfify'):
            entry = row1[2]
            for s, t in [('\u0320', '')]:
                entry = entry.replace(s, t)
            tokens = self.tokenizer({}, entry.strip().replace(' ', '_'), column='IPA')
            # Compute scan number from concept number and language number.
            page = int(concepts[row1[0]][1]) + int(int(row1[1]) > 31)
            scan = str(page + 18).rjust(4, '0')

            if row1[2].replace('_', '').replace('-', '').strip():
                phrase_data[row1[1]][row1[0]] = (row2[2], row1[2])
                args.writer.add_form_with_segments(
                    Value=row1[2],
                    Form=''.join(tokens),
                    Segments=tokens,
                    Profile=' '.join(self.tokenizer({}, entry.strip(), column='Grapheme')),
                    Source=['Gauchat1925[{0}]'.format(page)],
                    Language_ID=languages[row1[1]],
                    Parameter_ID=concepts[row1[0]][0],
                    Scan=scan,
                    ProsodicStructure=prosodic_string(tokens, _output='CcV'),
                    SegmentedValue=' '.join(self.tokenizer({}, entry, column='Graphemes'))
                )

        args.writer.cldf.add_component(
            'ExampleTable',
            'Alt_Transcription',
            {
                "name": "Concept_ID",
                "separator": " ",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#parameterReference",
            },
            {
                "name": "Form_ID",
                "separator": " ",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#formReference",
            },
        )
        args.writer.cldf.add_foreign_key('ExampleTable', 'Concept_ID', 'ParameterTable', 'ID')
        args.writer.cldf.add_foreign_key('ExampleTable', 'Form_ID', 'FormTable', 'ID')

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
                        Concept_ID=[concepts[cid][0] for cid in cids],
                        Form_ID=['{}-{}-1'.format(lid, concepts[cid][0]) for cid in cids],
                    ))
                except KeyError:
                    pass
