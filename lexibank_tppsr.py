from collections import OrderedDict, defaultdict

import attr
from pathlib import Path
from pylexibank import Concept, Language, FormSpec
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import progressbar

from lingpy import *
from clldutils.misc import slug
from segments.tokenizer import Tokenizer

from pyclts import CLTS

@attr.s
class CustomConcept(Concept):
    French_Gloss = attr.ib(default=None)
    Latin_Gloss = attr.ib(default=None)
    Number = attr.ib(default=None)

@attr.s
class CustomLanguage(Language):
    Number = attr.ib(default=None)
    Canton = attr.ib(default=None)


class Dataset(BaseDataset):
    id = "tppsr"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage
    form_spec = FormSpec(
            first_form_only=True,
            missing_data=("#NAME?", ),
            )

    def cmd_makecldf(self, args):
        args.writer.add_sources()

        data = self.raw_dir.read_csv('graphemes.tsv', delimiter='\t')
        args.writer.add_sources()
        
        concepts = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = '{0}_{1}'.format(
                        concept.id,
                        slug(concept.attributes['french']))
            args.writer.add_concept(
                    ID=idx,
                    Number=concept.number,
                    Name=concept.attributes['french'],
                    French_Gloss=concept.attributes['french'],
                    Latin_Gloss=concept.attributes['latin'],
                    Concepticon_ID=concept.concepticon_id,
                    Concepticon_Gloss=concept.concepticon_gloss
                    )
            concepts[concept.number] = idx
            
        languages = args.writer.add_languages(
                id_factory='Number')
        
        symbols = set()
        bow = 'a͜ó'[1]

        replacements = [
            #('\u033e', ''),
            #('\u0311', ''),
            #('\u1daa', ''),
            #('\u0331', '')
            #('\u0331', ''),
            #('\u0306', ''),
            #('\u0304', '')
            ]


        tk = Tokenizer(self.dir.joinpath('etc', 'orthography.tsv'),
                errors_replace=lambda x: '<'+x+'>')
        bads = set()
        bipa = CLTS().bipa
        for line in progressbar(self.raw_dir.read_csv('graphemes.tsv', delimiter='\t')):
            for segment in tk(line[3], column='IPA').split():
                if bipa[segment].type == 'unknownsound':
                    bads.add(line[3])

            if line[3] != '#NAME?':
                form = self.lexemes.get(line[3], line[3])
                for s, t in replacements:
                    form = form.replace(s, t)
                args.writer.add_form(
                        Value=line[3],
                        Form=form,
                        Parameter_ID=concepts[line[1]],
                        Language_ID=line[2],
                        Source=['Gauchat1925'])
        visited = set()
        for b in bads:
            segs = tk(b, column='Grapheme').split()
            segs2 = tk(b, column='IPA').split()
            for i, (s1, s2) in enumerate(zip(segs, segs2)):
                if s2[0] == '<':
                    try:
                        print(segs[i-1]+s1[1:-1]+'\t'+segs2[i-1])
                    except:
                        pass
            #print(b+'\t'+tk(b, column='IPA'))



