from collections import OrderedDict, defaultdict

import attr
from pathlib import Path
from pylexibank import Concept, Language, FormSpec, Lexeme
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import progressbar

from csvw.metadata import URITemplate

from lingpy import *
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
    SubGroup = attr.ib(default="Romance")
    DialectGroup = attr.ib(default=None)
    Population = attr.ib(default=None)
    SpeakerAge = attr.ib(default=None)
    SpeakerProficiency = attr.ib(default=None)
    SpeakerLanguageUse = attr.ib(default=None)
    SpeakerNote = attr.ib(default=None)


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
    form_spec = FormSpec(
            first_form_only=True,
            missing_data=("#NAME?", ),
            )

    def cmd_makecldf(self, args):
        args.writer.add_sources()
        
        # add URI template
        args.writer.cldf["FormTable", "Scan"].valueUrl = URITemplate('https://ia801505.us.archive.org/BookReader/BookReaderImages.php?zip=/28/items/gauchat-et-al-1925-tppsr/gauchat-et-al-1925-tppsr_jp2.zip&file=gauchat-et-al-1925-tppsr_jp2/gauchat-et-al-1925-tppsr_{Scan}.jp2&id=Z2F1Y2hhdC1ldC1hbC0xOTI1LXRwcHNy&scale=5')

        values = self.raw_dir.read_csv('tppsr-db-v20.txt', delimiter='\t')
        forms = self.raw_dir.read_csv(
                'tppsr-db-v20-ipa-narrow.txt',
                delimiter='\t')

        args.writer.add_sources()

        concepts = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = '{0}_{1}'.format(
                        concept.id,
                        slug(concept.attributes['french']))
            args.writer.add_concept(
                    ID=idx,
                    Number=concept.number,
                    Name=concept.gloss,
                    French_Gloss=concept.attributes['french'],
                    Latin_Gloss=concept.attributes['latin'],
                    Concepticon_ID=concept.concepticon_id,
                    Concepticon_Gloss=concept.concepticon_gloss
                    )
            concepts[concept.number] = (idx, concept.attributes['page'])
            
        languages = args.writer.add_languages(
                lookup_factory='Number')

        new_profile = defaultdict(int)

        for row1, row2 in progressbar(
                zip(values, forms),
                desc='cldfify'
                ):
            entry = row1[2]
            for s, t in [('\u0320', '')]:
                entry = entry.replace(s, t)
            graphemes = ' '.join(self.tokenizer({}, entry,
                column='Grapheme'))
            tokens = self.tokenizer({}, entry, column='IPA')
            segmented_value = self.tokenizer({}, entry, column='Graphemes')
            page = int(concepts[row1[0]][1]) + (
                    1 if int(row1[1]) > 31 else 0)
            prosody = prosodic_string(tokens, _output='CcV')

            if row1[2].replace('_', '').replace('-', '').strip():
                lex = args.writer.add_form_with_segments(
                        Value=row1[2],
                        Form=''.join(tokens),
                        Segments=tokens,
                        Profile=graphemes,
                        Source=['Gauchat1925[{0}]'.format(page)],
                        Language_ID=languages[row1[1]],
                        Parameter_ID=concepts[row1[0]][0],
                        Scan=str(page+18).rjust(4, '0'),
                        ProsodicStructure=prosody,
                        SegmentedValue=segmented_value
                        )


