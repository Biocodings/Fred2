# This code is part of the Fred2 distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.
"""
.. module:: Reader
   :synopsis: Module handles reading of files. line reading, FASTA reading, annovar reading
.. moduleauthor:: brachvogel, schubert

"""

import warnings
import os
import re

from Bio.SeqIO.FastaIO import SimpleFastaParser

from Fred2.Core.Peptide import Peptide
from Fred2.Core.Variant import Variant, VariationType, MutationSyntax


####################################
#       F A S T A  -  R E A D E R
####################################
def read_fasta(files, in_type=Peptide, id_position=1):
    """
    Generator function:

    Read a (couple of) peptide, protein or rna sequence from a FASTA file.
    User needs to specify the correct type of the underlying sequences. It can
    either be: Peptide, Protein or Transcript (for RNA).

    :param files: A (list) of file names to read in
    :in_type files: list(str) or str
    :param in_type: The type to read in
    :type in_type: :class:`~Fred2.Core.Peptide.Peptide` or :class:`~Fred2.Core.Transcript.Transcript`
                or :class:`~Fred2.Core.Protein.Protein`
    :param int id_position: the position of the id specified counted by |
    :returns: a list of the specified sequence type derived from the FASTA file sequences.
    :rtype: (list(:attr:`in_type`))
    :raises ValueError: if a file is not readable
    """

    if isinstance(files, basestring):
            files = [files]
    else:
            if any(not os.path.exists(f) for f in files):
                raise ValueError("Specified Files do not exist")

    collect = set()
    # open all specified files:
    for name in files:
        with open(name, 'r') as handle:
            # iterate over all FASTA entries:
            for _id, seq in SimpleFastaParser(handle):
                # generate element:
                try:
                    _id = _id.split("|")[id_position]
                except IndexError:
                   _id = _id

                try:
                    collect.add(in_type(seq.strip().upper(), transcript_id=_id))
                except TypeError:
                    collect.add(in_type(seq.strip().upper()))
    return list(collect)



####################################
#       L I N E  -  R E A D E R
####################################
def read_lines(files, in_type=Peptide):
    """
    Generator function:

    Read a sequence directly from a line. User needs to manually specify the 
    correct type of the underlying data. It can either be:
    Peptide, Protein or Transcript, Allele.

    :param files: a list of strings of absolute file names that are to be read.
    :in_type files: list(str) or str
    :param in_type: Possible in_type are :class:`~Fred2.Core.Peptide.Peptide`, :class:`~Fred2.Core.Protein.Protein`,
                 :class:`~Fred2.Core.Transcript.Transcript`, and :class:`~Fred2.Core.Allele.Allele`.
    :type in_type: :class:`~Fred2.Core.Peptide.Peptide` or :class:`~Fred2.Core.Protein.Protein` or
                :class:`~Fred2.Core.Transcript.Transcript` or :class:`~Fred2.Core.Allele.Allele`
    :returns: A list of the specified objects
    :rtype: (list(:attr:`in_type`))
    :raises IOError: if a file is not readable
    """

    if isinstance(files, basestring):
            files = [files]
    else:
            if any(not os.path.exists(f) for f in files):
                raise IOError("Specified Files do not exist")

    collect = set()
    #alternative to using strings is like: cf = getattr(Fred2.Core, "Protein"/"Peptide"/"Allele"/...all in core)
    for name in files:
        with open(name, 'r') as handle:
            # iterate over all lines:
            for line in handle:
                # generate element:
                collect.add(in_type(line.strip().upper()))

    return list(collect)


#####################################
#       A N N O V A R  -  R E A D E R
#####################################
def read_annovar_exonic(annovar_file, gene_filter=None, experimentalDesig=None):
    """
    Reads an gene-based ANNOVAR output file and generates :class:`~Fred2.Core.Variant.Variant` objects containing
    all annotated :class:`~Fred2.Core.Transcript.Transcript` ids an outputs a list :class:`~Fred2.Core.Variant.Variant`.

    :param str annovar_file: The path ot the ANNOVAR file
    :param list(str) gene_filter: A list of gene names of interest (only variants associated with these genes
                                  are generated)
    :return: List of :class:`~Fred2.Core.Variant.Variants fully annotated
    :rtype: list(:class:`~Fred2.Core.Variant.Variant`)
    """

    vars = []
    gene_filter = gene_filter if gene_filter is not None else []

    #fgd3:nm_001083536:exon6:c.g823a:p.v275i,fgd3:nm_001286993:exon6:c.g823a:p.v275i,fgd3:nm_033086:exon6:c.g823a:p.v275i
    #RE = re.compile("\w+:(\w+):exon\d+:c.(\D*)(\d+)_*(\d*)(\D\w*):p.\w+:\D*->\D*:(\D).*?,")
    #RE = re.compile("\w+:(\w+):exon\d+:c.(\D*)(\d+)_*(\d*)(\D\w*):p.(\D*)(\d+)_*(\d*)(\D\w*):(\D).*?,")
    RE = re.compile("((\w+):(\w+):exon\d+:c.\D*(\d+)\D\w*:p.\D*(\d+)\D\w*)")
    type_mapper = {('synonymous', 'snv'): VariationType.SNP,
                   ('nonsynonymous', 'snv'): VariationType.SNP,
                   ('stoploss', 'snv'): VariationType.SNP,
                   ('stopgain', 'snv'): VariationType.SNP,
                   ('nonframeshift', 'deletion'): VariationType.DEL,
                   ('frameshift', 'deletion'): VariationType.FSDEL,
                   ('nonframeshift', 'insertion'): VariationType.INS,
                   ('frameshift', 'insertion'): VariationType.FSINS}
    with open(annovar_file, "r") as f:
        for line in f:
            mut_id, mut_type, line, chrom, genome_start, genome_stop, ref, alt, zygos = map(lambda x: x.strip().lower(),
                                                                                    line.split("\t")[:9])
            #print ref, alt

            #test if its a intersting snp

            gene = line.split(":")[0].strip().upper()

            if gene not in gene_filter and len(gene_filter):
                continue

            if gene == "UNKNOWN":
                warnings.warn("Skipping UNKWON gene")
                continue

           # print "Debug ", gene, type.split(),mut_id
            #print "Debug ", line, RE.findall(line), type, zygos
            coding = {}
            for nm_id_pos in RE.findall(line):
                mutation_string, geneID, nm_id, trans_pos, prot_start = nm_id_pos
                #print "Debug ",nm_id_pos

                nm_id = nm_id.upper()
                _,_, _, trans_coding, prot_coding = mutation_string.split(":")
                #internal transcript and protein position start at 0!
                coding[nm_id] = MutationSyntax(nm_id, int(trans_pos)-1, int(prot_start)-1, trans_coding, prot_coding,
                                               geneID=geneID.upper())

            ty = tuple(mut_type.split())

            vars.append(
                Variant(mut_id, type_mapper.get(ty, VariationType.UNKNOWN), chrom, int(genome_start), ref.upper(),
                        alt.upper(), coding, zygos == "hom", ty[0] == "synonymous",
                        experimentalDesign=experimentalDesig))
    return vars
