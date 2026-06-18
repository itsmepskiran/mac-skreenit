"""
NLP Analysis Service for Video Interview Transcripts
Analyzes communication skills, grammar, sentence formation, and vocabulary.

Required libraries:
- language_tool_python: Grammar checking
- spacy: NLP pipeline (install with: python -m spacy download en_core_web_sm)
- textstat: Readability and complexity metrics
- nltk: Sentence tokenization (already installed with whisper)
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

# Lazy imports to avoid startup errors if libraries not installed
logger = logging.getLogger(__name__)

# Global instances (lazy loaded)
_nlp = None
_language_tool = None
_textstat = None


def _get_nlp():
    """Lazy load spaCy NLP model."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except ImportError:
            logger.warning("spaCy not installed. Sentence analysis will be limited.")
        except OSError as e:
            logger.warning(f"spaCy model not found. Run: python -m spacy download en_core_web_sm. Error: {e}")
    return _nlp


def _get_language_tool():
    """Lazy load LanguageTool for grammar checking."""
    global _language_tool
    if _language_tool is None:
        try:
            import language_tool_python
            _language_tool = language_tool_python.LanguageTool('en-US')
            logger.info("LanguageTool initialized successfully")
        except ImportError:
            logger.warning("language_tool_python not installed. Grammar checking disabled.")
        except Exception as e:
            logger.warning(f"LanguageTool initialization failed: {e}")
    return _language_tool


def _get_textstat():
    """Lazy load textstat for readability metrics."""
    global _textstat
    if _textstat is None:
        try:
            import textstat
            _textstat = textstat
            logger.info("textstat loaded successfully")
        except ImportError:
            logger.warning("textstat not installed. Readability metrics will be limited.")
    return _textstat


class NLPAnalysisService:
    """
    Comprehensive NLP analysis service for interview transcripts.
    Analyzes grammar, sentence structure, vocabulary, and communication skills.
    """
    
    def __init__(self):
        """Initialize the NLP analysis service with lazy-loaded components."""
        self.nlp = _get_nlp()
        self.lang_tool = _get_language_tool()
        self.textstat = _get_textstat()
    
    def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Main method to analyze a transcript comprehensively.
        
        Args:
            transcript: The text transcript to analyze
            
        Returns:
            Dictionary containing all analysis results
        """
        if not transcript or not transcript.strip():
            return self._empty_result()
        
        # Clean transcript
        clean_text = self._clean_text(transcript)
        
        # Run all analyses
        grammar_result = self.analyze_grammar(clean_text)
        sentence_result = self.analyze_sentences(clean_text)
        vocabulary_result = self.analyze_vocabulary(clean_text)
        communication_result = self.calculate_communication_score(
            grammar_result, sentence_result, vocabulary_result, clean_text
        )
        
        return {
            "grammar": grammar_result,
            "sentence_formation": sentence_result,
            "vocabulary": vocabulary_result,
            "communication_skills": communication_result,
            "summary": {
                "grammar_score": grammar_result.get("score", 0),
                "sentence_score": sentence_result.get("score", 0),
                "vocabulary_score": vocabulary_result.get("score", 0),
                "communication_score": communication_result.get("score", 0)
            }
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for analysis."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure when no transcript provided."""
        return {
            "grammar": {"score": 0, "error_count": 0, "issues": []},
            "sentence_formation": {"score": 0, "avg_length": 0, "complexity": "unknown"},
            "vocabulary": {"score": 0, "diversity": 0, "unique_words": 0},
            "communication_skills": {"score": 0, "level": "unknown"},
            "summary": {
                "grammar_score": 0,
                "sentence_score": 0,
                "vocabulary_score": 0,
                "communication_score": 0
            }
        }
    
    # =========================================================================
    # GRAMMAR ANALYSIS
    # =========================================================================
    
    def analyze_grammar(self, text: str) -> Dict[str, Any]:
        """
        Analyze grammar and spelling errors using LanguageTool.
        
        Returns:
            {
                "score": 0-100,
                "error_count": int,
                "errors_per_100_words": float,
                "issues": [
                    {
                        "message": str,
                        "type": str,
                        "category": str,
                        "position": (start, end),
                        "suggestions": [str]
                    }
                ],
                "error_breakdown": {
                    "spelling": int,
                    "grammar": int,
                    "punctuation": int,
                    "style": int
                }
            }
        """
        result = {
            "score": 100,
            "error_count": 0,
            "errors_per_100_words": 0.0,
            "issues": [],
            "error_breakdown": {
                "spelling": 0,
                "grammar": 0,
                "punctuation": 0,
                "style": 0
            }
        }
        
        if not self.lang_tool:
            result["note"] = "Grammar checking unavailable (language_tool_python not installed)"
            return result
        
        try:
            # Get word count for normalization
            words = text.split()
            word_count = len(words)
            
            # Check for errors
            matches = self.lang_tool.check(text)
            
            result["error_count"] = len(matches)
            result["errors_per_100_words"] = round((len(matches) / word_count) * 100, 2) if word_count > 0 else 0
            
            # Categorize and format errors
            for match in matches:
                error_type = self._categorize_grammar_error(match)
                result["error_breakdown"][error_type] += 1
                
                # Get match length - handle both 'length' attribute and calculated length
                match_length = getattr(match, 'length', None)
                if match_length is None and hasattr(match, 'offset'):
                    # Calculate length from contextavailable
                    match_length = len(match.context) if hasattr(match, 'context') else 0
                
                issue = {
                    "message": match.message,
                    "type": error_type,
                    "category": match.category if hasattr(match, 'category') else 'unknown',
                    "position": (match.offset, match.offset + (match_length or 0)),
                    "context": text[max(0, match.offset - 20):match.offset + (match_length or 0) + 20],
                    "suggestions": match.replacements[:3] if match.replacements else []
                }
                result["issues"].append(issue)
            
            # Calculate score (100 - penalty for errors)
            # Penalty: 5 points per error per 100 words, max 100 point deduction
            penalty = min(100, result["errors_per_100_words"] * 5)
            result["score"] = max(0, 100 - penalty)
            
        except Exception as e:
            logger.error(f"Grammar analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _categorize_grammar_error(self, match) -> str:
        """Categorize a grammar error into spelling, grammar, punctuation, or style."""
        category = str(match.category).upper() if hasattr(match, 'category') else ''
        rule_id = str(match.ruleId).upper() if hasattr(match, 'ruleId') else ''
        
        # Spelling errors
        if 'SPELL' in category or 'SPELL' in rule_id or 'MORFOLOGIK' in rule_id:
            return 'spelling'
        
        # Punctuation errors
        if 'PUNCT' in category or 'PUNCTUATION' in category:
            return 'punctuation'
        
        # Style issues
        if 'STYLE' in category or 'TYPOS' in category:
            return 'style'
        
        # Default to grammar
        return 'grammar'
    
    # =========================================================================
    # SENTENCE FORMATION ANALYSIS
    # =========================================================================
    
    def analyze_sentences(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentence structure, length, and complexity using spaCy.
        
        Returns:
            {
                "score": 0-100,
                "total_sentences": int,
                "avg_sentence_length": float,
                "avg_words_per_sentence": float,
                "complexity": "simple" | "moderate" | "complex",
                "sentence_types": {
                    "simple": int,
                    "compound": int,
                    "complex": int,
                    "fragment": int
                },
                "issues": [
                    {
                        "type": "run_on" | "fragment" | "awkward",
                        "sentence": str,
                        "suggestion": str
                    }
                ],
                "readability": {
                    "flesch_kincaid_grade": float,
                    "flesch_reading_ease": float,
                    "avg_syllables_per_word": float
                }
            }
        """
        result = {
            "score": 50,
            "total_sentences": 0,
            "avg_sentence_length": 0.0,
            "avg_words_per_sentence": 0.0,
            "complexity": "unknown",
            "sentence_types": {
                "simple": 0,
                "compound": 0,
                "complex": 0,
                "fragment": 0
            },
            "issues": [],
            "readability": {}
        }
        
        try:
            # Use spaCy if available
            if self.nlp:
                doc = self.nlp(text)
                sentences = list(doc.sents)
                result["total_sentences"] = len(sentences)
                
                if sentences:
                    # Calculate average sentence length
                    sentence_lengths = [len([token for token in sent if not token.is_punct]) for sent in sentences]
                    result["avg_sentence_length"] = round(sum(sentence_lengths) / len(sentences), 2)
                    result["avg_words_per_sentence"] = result["avg_sentence_length"]
                    
                    # Analyze sentence types
                    for sent in sentences:
                        sent_type = self._classify_sentence_type(sent)
                        result["sentence_types"][sent_type] += 1
                        
                        # Check for issues
                        issue = self._detect_sentence_issue(sent)
                        if issue:
                            result["issues"].append(issue)
                    
                    # Determine overall complexity
                    result["complexity"] = self._determine_complexity(result)
                    
                    # Calculate score
                    result["score"] = self._calculate_sentence_score(result)
            
            # Add readability metrics if textstat available
            if self.textstat:
                result["readability"] = {
                    "flesch_kincaid_grade": self.textstat.flesch_kincaid_grade(text),
                    "flesch_reading_ease": self.textstat.flesch_reading_ease(text),
                    "avg_syllables_per_word": round(self.textstat.syllable_count(text) / max(1, len(text.split())), 2),
                    "coleman_liau_index": self.textstat.coleman_liau_index(text),
                    "automated_readability_index": self.textstat.automated_readability_index(text)
                }
            
        except Exception as e:
            logger.error(f"Sentence analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _classify_sentence_type(self, sent) -> str:
        """Classify sentence as simple, compound, complex, or fragment."""
        # Count clauses by looking for coordinating conjunctions and subordinating conjunctions
        has_subordinator = any(token.dep_ in ["mark", "advcl"] for token in sent)
        has_coordinator = any(token.dep_ == "cc" for token in sent if token.text.lower() in ["and", "but", "or", "nor", "yet", "so"])
        
        # Check for main verb
        has_verb = any(token.pos_ in ["VERB", "AUX"] for token in sent if token.dep_ in ["ROOT", "conj"])
        
        # Fragment: no main verb
        if not has_verb:
            return "fragment"
        
        # Complex: has subordinating conjunction
        if has_subordinator:
            return "complex"
        
        # Compound: has coordinating conjunction with multiple verbs
        verb_count = sum(1 for token in sent if token.pos_ in ["VERB", "AUX"] and token.dep_ in ["ROOT", "conj"])
        if has_coordinator and verb_count > 1:
            return "compound"
        
        return "simple"
    
    def _detect_sentence_issue(self, sent) -> Optional[Dict[str, Any]]:
        """Detect issues like run-on sentences or fragments."""
        sent_text = sent.text.strip()
        word_count = len([token for token in sent if not token.is_punct])
        
        # Run-on sentence: too long without proper punctuation
        if word_count > 35:
            return {
                "type": "run_on",
                "sentence": sent_text[:100] + "..." if len(sent_text) > 100 else sent_text,
                "word_count": word_count,
                "suggestion": "Consider breaking this into shorter sentences for clarity"
            }
        
        # Fragment: very short without verb
        if word_count < 3:
            return {
                "type": "fragment",
                "sentence": sent_text,
                "suggestion": "This appears to be an incomplete sentence"
            }
        
        return None
    
    def _determine_complexity(self, result: Dict) -> str:
        """Determine overall text complexity."""
        avg_len = result["avg_sentence_length"]
        types = result["sentence_types"]
        total = result["total_sentences"]
        
        if total == 0:
            return "unknown"
        
        # Calculate complexity ratio
        complex_ratio = (types["complex"] + types["compound"]) / total
        
        if avg_len > 20 or complex_ratio > 0.5:
            return "complex"
        elif avg_len > 12 or complex_ratio > 0.3:
            return "moderate"
        else:
            return "simple"
    
    def _calculate_sentence_score(self, result: Dict) -> int:
        """Calculate sentence formation score (0-100)."""
        score = 50  # Base score
        
        # Reward good average length (12-20 words ideal)
        avg_len = result["avg_sentence_length"]
        if 12 <= avg_len <= 20:
            score += 20
        elif 10 <= avg_len <= 25:
            score += 10
        elif avg_len > 30:
            score -= 10  # Too long
        
        # Reward sentence variety
        types = result["sentence_types"]
        total = result["total_sentences"]
        if total > 0:
            variety_score = 0
            if types["simple"] > 0:
                variety_score += 5
            if types["compound"] > 0:
                variety_score += 5
            if types["complex"] > 0:
                variety_score += 10
            score += variety_score
        
        # Penalize fragments
        fragment_penalty = types["fragment"] * 5
        score -= fragment_penalty
        
        # Penalize run-ons (issues)
        run_on_penalty = sum(1 for issue in result["issues"] if issue["type"] == "run_on") * 5
        score -= run_on_penalty
        
        return max(0, min(100, score))
    
    # =========================================================================
    # VOCABULARY ANALYSIS
    # =========================================================================
    
    def analyze_vocabulary(self, text: str) -> Dict[str, Any]:
        """
        Analyze vocabulary richness, diversity, and sophistication.
        
        Returns:
            {
                "score": 0-100,
                "total_words": int,
                "unique_words": int,
                "type_token_ratio": float,  # Unique/Total ratio
                "diversity_score": float,
                "sophistication": {
                    "basic_words": int,
                    "intermediate_words": int,
                    "advanced_words": int,
                    "advanced_word_ratio": float
                },
                "repetition": {
                    "repeated_words": [{"word": str, "count": int}],
                    "repetition_score": float
                },
                "word_frequency_tier": str  # "basic" | "intermediate" | "advanced"
            }
        """
        result = {
            "score": 50,
            "total_words": 0,
            "unique_words": 0,
            "type_token_ratio": 0.0,
            "diversity_score": 0.0,
            "sophistication": {
                "basic_words": 0,
                "intermediate_words": 0,
                "advanced_words": 0,
                "advanced_word_ratio": 0.0
            },
            "repetition": {
                "repeated_words": [],
                "repetition_score": 100
            },
            "word_frequency_tier": "unknown"
        }
        
        try:
            # Tokenize and clean
            words = self._tokenize_words(text)
            result["total_words"] = len(words)
            
            if not words:
                return result
            
            # Calculate basic metrics
            unique_words = set(words)
            result["unique_words"] = len(unique_words)
            result["type_token_ratio"] = round(len(unique_words) / len(words), 3) if words else 0
            result["diversity_score"] = result["type_token_ratio"] * 100
            
            # Analyze word sophistication
            sophistication = self._analyze_word_sophistication(words)
            result["sophistication"] = sophistication
            
            # Analyze repetition
            repetition = self._analyze_repetition(words)
            result["repetition"] = repetition
            
            # Determine frequency tier
            if sophistication["advanced_word_ratio"] > 0.2:
                result["word_frequency_tier"] = "advanced"
            elif sophistication["advanced_word_ratio"] > 0.1:
                result["word_frequency_tier"] = "intermediate"
            else:
                result["word_frequency_tier"] = "basic"
            
            # Calculate overall vocabulary score
            result["score"] = self._calculate_vocabulary_score(result)
            
        except Exception as e:
            logger.error(f"Vocabulary analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words, removing punctuation and stopwords."""
        # Simple tokenization
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Remove common stopwords (basic list)
        stopwords = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
            'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
            'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
            'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'um', 'uh', 'like'
        }
        
        return [w for w in words if w not in stopwords and len(w) > 1]
    
    def _analyze_word_sophistication(self, words: List[str]) -> Dict[str, Any]:
        """Categorize words by sophistication level."""
        # Common basic words (top 500 most frequent English words)
        basic_words = {
            'time', 'year', 'people', 'way', 'day', 'man', 'woman', 'child', 'world', 'life',
            'hand', 'part', 'place', 'case', 'week', 'company', 'system', 'program', 'question',
            'work', 'government', 'number', 'night', 'point', 'home', 'water', 'room', 'mother',
            'area', 'money', 'story', 'fact', 'month', 'lot', 'right', 'study', 'book', 'eye',
            'job', 'word', 'business', 'issue', 'side', 'kind', 'head', 'house', 'service', 'friend',
            'father', 'power', 'hour', 'game', 'line', 'end', 'member', 'law', 'car', 'city',
            'name', 'team', 'minute', 'idea', 'kid', 'body', 'information', 'back', 'parent', 'face',
            'others', 'level', 'office', 'door', 'health', 'person', 'art', 'war', 'history', 'party',
            'result', 'change', 'morning', 'reason', 'research', 'girl', 'guy', 'moment', 'air', 'teacher',
            'force', 'education', 'foot', 'boy', 'age', 'policy', 'process', 'music', 'market', 'sense',
            'national', 'new', 'good', 'bad', 'great', 'little', 'own', 'other', 'old', 'right',
            'big', 'high', 'different', 'small', 'large', 'next', 'early', 'young', 'important', 'public',
            'bad', 'same', 'able', 'think', 'help', 'get', 'give', 'make', 'go', 'know', 'take', 'see',
            'come', 'want', 'look', 'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave',
            'call', 'keep', 'let', 'begin', 'show', 'hear', 'play', 'run', 'move', 'live', 'believe',
            'bring', 'happen', 'write', 'provide', 'sit', 'stand', 'lose', 'pay', 'meet', 'include', 'continue',
            'set', 'learn', 'change', 'lead', 'understand', 'watch', 'follow', 'stop', 'create', 'speak',
            'read', 'allow', 'add', 'spend', 'grow', 'open', 'walk', 'win', 'offer', 'remember', 'love',
            'consider', 'appear', 'buy', 'wait', 'serve', 'die', 'send', 'expect', 'build', 'stay', 'fall',
            'cut', 'reach', 'kill', 'remain', 'suggest', 'raise', 'pass', 'sell', 'require', 'report',
            'decide', 'pull', 'experience', 'actually', 'probably', 'basically', 'really', 'very', 'quite'
        }
        
        # Advanced/academic words
        advanced_words = {
            'accomplish', 'acquire', 'adequate', 'adjacent', 'advantage', 'advocate', 'affect', 'allocate',
            'alternative', 'ambitious', 'analyze', 'anticipate', 'apparent', 'appreciate', 'approach',
            'appropriate', 'articulate', 'assess', 'assign', 'assume', 'assure', 'attain', 'attribute',
            'authentic', 'awareness', 'beneficial', 'capacity', 'challenge', 'circumstance', 'collaborate',
            'commitment', 'comprehensive', 'concentrate', 'concept', 'conclude', 'concrete', 'confer',
            'confident', 'consequence', 'considerable', 'consistent', 'consolidate', 'constitute', 'construct',
            'consult', 'contemporary', 'context', 'contribute', 'convention', 'convince', 'cooperate',
            'coordinate', 'corporate', 'correspond', 'crucial', 'demonstrate', 'derive', 'determine',
            'develop', 'device', 'diminish', 'discern', 'discipline', 'disclose', 'distinguish', 'diverse',
            'domain', 'dominant', 'dynamic', 'effective', 'efficient', 'elaborate', 'elicit', 'emerge',
            'emphasize', 'empirical', 'enable', 'encompass', 'endeavor', 'enhance', 'ensure', 'entity',
            'equivalent', 'establish', 'evaluate', 'evident', 'evolve', 'exceed', 'exhibit', 'expand',
            'expertise', 'explicit', 'exploit', 'explore', 'facilitate', 'factor', 'feasible', 'feature',
            'federal', 'flexible', 'fluctuate', 'formulate', 'foundation', 'framework', 'function', 'fundamental',
            'generate', 'guarantee', 'hierarchy', 'hypothesis', 'identify', 'illustrate', 'implement', 'implication',
            'implicit', 'imply', 'impose', 'incentive', 'incident', 'incline', 'incorporate', 'increment',
            'indicate', 'indigenous', 'individual', 'induce', 'inevitable', 'influence', 'infrastructure',
            'initial', 'initiate', 'innovation', 'input', 'instance', 'institution', 'integral', 'integrate',
            'integrity', 'intelligent', 'intense', 'interact', 'interface', 'internal', 'interpret', 'interval',
            'intervene', 'intrinsic', 'invest', 'investigate', 'involve', 'isolate', 'justify', 'label',
            'legitimate', 'liberal', 'link', 'locate', 'logic', 'maintain', 'major', 'manipulate', 'mechanism',
            'mediate', 'medium', 'mental', 'method', 'migrate', 'minimal', 'minimize', 'minor', 'mode', 'modify',
            'monitor', 'multiple', 'municipal', 'mutual', 'narrative', 'negate', 'negotiate', 'neutral', 'nevertheless',
            'norm', 'notion', 'nuclear', 'objective', 'obligation', 'obscure', 'observe', 'obtain', 'occupy',
            'occur', 'offset', 'ongoing', 'option', 'orient', 'outcome', 'output', 'overall', 'overlap', 'overseas',
            'parameter', 'participate', 'partner', 'passive', 'perceive', 'permanent', 'permit', 'persist',
            'perspective', 'phenomenon', 'philosophy', 'plausible', 'pleasant', 'policy', 'poll', 'portion',
            'potential', 'practitioner', 'precede', 'precise', 'predict', 'predominant', 'preliminary', 'premise',
            'premium', 'preserve', 'previous', 'primary', 'prime', 'principal', 'principle', 'priority', 'privilege',
            'proceed', 'process', 'professional', 'profound', 'project', 'prominent', 'promote', 'proportion',
            'prospect', 'protocol', 'provide', 'psychology', 'publish', 'purchase', 'pursue', 'qualitative',
            'quote', 'radical', 'random', 'range', 'ratio', 'rational', 'react', 'realm', 'rebel', 'recall',
            'recession', 'recognize', 'recommend', 'redundant', 'reference', 'refine', 'reflect', 'reform',
            'region', 'regulate', 'reinforce', 'reject', 'relate', 'relevant', 'reliable', 'reluctant', 'rely',
            'remain', 'remarkable', 'remedy', 'remote', 'render', 'renew', 'represent', 'reproduce', 'require',
            'reserve', 'reside', 'resolve', 'resource', 'respond', 'restore', 'restrict', 'retain', 'reveal',
            'revenue', 'reverse', 'revise', 'revolution', 'rigid', 'role', 'route', 'scenario', 'schedule',
            'scheme', 'scope', 'sector', 'secure', 'seek', 'segment', 'select', 'seminar', 'senate', 'senior',
            'sequence', 'series', 'session', 'settle', 'severe', 'shift', 'significant', 'similar', 'simulate',
            'simultaneous', 'site', 'slight', 'solar', 'sole', 'source', 'specific', 'specify', 'sphere', 'spite',
            'stable', 'standard', 'statistic', 'status', 'stimulate', 'strategy', 'stress', 'structure', 'style',
            'submit', 'subsequent', 'subsidy', 'substantial', 'succeed', 'successor', 'sufficient', 'sum', 'summary',
            'supplement', 'supply', 'support', 'suppress', 'surplus', 'survey', 'survive', 'suspend', 'sustain',
            'symbol', 'symptom', 'tactic', 'target', 'team', 'technical', 'technology', 'temporary', 'tense',
            'terminal', 'theme', 'thereby', 'thesis', 'threat', 'threshold', 'tight', 'tissue', 'topic', 'trace',
            'tradition', 'traffic', 'tragedy', 'transfer', 'transform', 'transit', 'transmit', 'transparent',
            'transport', 'treat', 'treaty', 'trend', 'trial', 'trigger', 'triple', 'ultimate', 'undergo', 'uniform',
            'union', 'unique', 'unity', 'universe', 'unlike', 'update', 'upgrade', 'uphold', 'urban', 'urge',
            'utilize', 'valid', 'validate', 'variable', 'variation', 'variety', 'various', 'vast', 'vehicle',
            'version', 'via', 'victim', 'virtual', 'visible', 'vision', 'visual', 'volume', 'voluntary', 'vote',
            'welfare', 'whereas', 'widespread', 'wisdom', 'withdraw', 'withstand', 'workforce', 'worldwide', 'yield',
            'zone', 'perspective', 'initiative', 'methodology', 'implementation', 'comprehensive', 'strategic'
        }
        
        basic_count = 0
        advanced_count = 0
        intermediate_count = 0
        
        for word in words:
            if word in basic_words:
                basic_count += 1
            elif word in advanced_words:
                advanced_count += 1
            else:
                intermediate_count += 1
        
        total = len(words)
        return {
            "basic_words": basic_count,
            "intermediate_words": intermediate_count,
            "advanced_words": advanced_count,
            "advanced_word_ratio": round(advanced_count / total, 3) if total > 0 else 0
        }
    
    def _analyze_repetition(self, words: List[str]) -> Dict[str, Any]:
        """Analyze word repetition patterns."""
        word_counts = Counter(words)
        total = len(words)
        
        # Find words repeated more than 3 times (excluding common words)
        repeated = [
            {"word": word, "count": count}
            for word, count in word_counts.most_common(10)
            if count > 3
        ]
        
        # Calculate repetition score (higher = less repetition = better)
        if total == 0:
            repetition_score = 100
        else:
            # Penalize for high-frequency words
            max_freq = word_counts.most_common(1)[0][1] if word_counts else 0
            max_ratio = max_freq / total
            repetition_score = max(0, 100 - (max_ratio * 100))
        
        return {
            "repeated_words": repeated,
            "repetition_score": round(repetition_score, 2)
        }
    
    def _calculate_vocabulary_score(self, result: Dict) -> int:
        """Calculate overall vocabulary score (0-100)."""
        score = 50  # Base score
        
        # Type-Token Ratio (diversity)
        ttr = result["type_token_ratio"]
        if ttr > 0.7:
            score += 20  # Excellent diversity
        elif ttr > 0.5:
            score += 10  # Good diversity
        elif ttr < 0.3:
            score -= 10  # Poor diversity
        
        # Advanced word usage
        adv_ratio = result["sophistication"]["advanced_word_ratio"]
        if adv_ratio > 0.15:
            score += 15
        elif adv_ratio > 0.08:
            score += 10
        elif adv_ratio > 0.03:
            score += 5
        
        # Repetition penalty
        rep_score = result["repetition"]["repetition_score"]
        if rep_score < 70:
            score -= 10
        elif rep_score > 90:
            score += 5
        
        return max(0, min(100, score))
    
    # =========================================================================
    # COMMUNICATION SKILLS SCORE
    # =========================================================================
    
    def calculate_communication_score(
        self,
        grammar: Dict,
        sentences: Dict,
        vocabulary: Dict,
        text: str
    ) -> Dict[str, Any]:
        """
        Calculate overall communication skills score combining all metrics.
        
        Returns:
            {
                "score": 0-100,
                "level": "beginner" | "intermediate" | "advanced" | "expert",
                "strengths": [str],
                "areas_for_improvement": [str],
                "detailed_scores": {
                    "grammar": int,
                    "sentence_formation": int,
                    "vocabulary": int,
                    "clarity": int,
                    "engagement": int
                }
            }
        """
        result = {
            "score": 0,
            "level": "unknown",
            "strengths": [],
            "areas_for_improvement": [],
            "detailed_scores": {
                "grammar": grammar.get("score", 0),
                "sentence_formation": sentences.get("score", 0),
                "vocabulary": vocabulary.get("score", 0),
                "clarity": 0,
                "engagement": 0
            }
        }
        
        try:
            # Calculate clarity score (based on sentence structure and grammar)
            clarity_score = (
                grammar.get("score", 0) * 0.4 +
                sentences.get("score", 0) * 0.6
            )
            result["detailed_scores"]["clarity"] = round(clarity_score)
            
            # Calculate engagement score (based on vocabulary and sentence variety)
            engagement_score = vocabulary.get("score", 0)
            if sentences.get("sentence_types"):
                types = sentences["sentence_types"]
                total = sentences["total_sentences"]
                if total > 0:
                    # Reward variety
                    variety = sum(1 for v in types.values() if v > 0)
                    engagement_score += variety * 3
            result["detailed_scores"]["engagement"] = min(100, round(engagement_score))
            
            # Calculate overall communication score
            weights = {
                "grammar": 0.25,
                "sentence_formation": 0.25,
                "vocabulary": 0.25,
                "clarity": 0.15,
                "engagement": 0.10
            }
            
            total_score = sum(
                result["detailed_scores"][key] * weight
                for key, weight in weights.items()
            )
            result["score"] = round(total_score)
            
            # Determine level
            if result["score"] >= 85:
                result["level"] = "expert"
            elif result["score"] >= 70:
                result["level"] = "advanced"
            elif result["score"] >= 50:
                result["level"] = "intermediate"
            else:
                result["level"] = "beginner"
            
            # Identify strengths
            if grammar.get("score", 0) >= 80:
                result["strengths"].append("Excellent grammar and spelling")
            if sentences.get("score", 0) >= 80:
                result["strengths"].append("Well-structured sentences")
            if vocabulary.get("score", 0) >= 80:
                result["strengths"].append("Rich and diverse vocabulary")
            if clarity_score >= 80:
                result["strengths"].append("Clear and articulate communication")
            
            # Identify areas for improvement
            if grammar.get("error_count", 0) > 5:
                result["areas_for_improvement"].append("Reduce grammatical errors")
            if sentences.get("avg_sentence_length", 0) > 25:
                result["areas_for_improvement"].append("Use shorter, clearer sentences")
            if vocabulary.get("type_token_ratio", 0) < 0.4:
                result["areas_for_improvement"].append("Expand vocabulary diversity")
            if vocabulary.get("repetition", {}).get("repetition_score", 100) < 70:
                result["areas_for_improvement"].append("Reduce word repetition")
            
            # Add specific grammar issues
            if grammar.get("error_breakdown"):
                breakdown = grammar["error_breakdown"]
                if breakdown.get("spelling", 0) > 2:
                    result["areas_for_improvement"].append("Improve spelling accuracy")
                if breakdown.get("punctuation", 0) > 2:
                    result["areas_for_improvement"].append("Review punctuation rules")
            
        except Exception as e:
            logger.error(f"Communication score calculation failed: {e}")
            result["error"] = str(e)
        
        return result


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def analyze_communication(transcript: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a transcript.
    
    Args:
        transcript: The text to analyze
        
    Returns:
        Complete analysis results
    """
    service = NLPAnalysisService()
    return service.analyze_transcript(transcript)
