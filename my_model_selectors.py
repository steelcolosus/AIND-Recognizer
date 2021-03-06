import math
import statistics
import warnings

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import KFold
from asl_utils import combine_sequences


class ModelSelector(object):
    '''
    base class for model selection (strategy design pattern)
    '''

    def __init__(self, all_word_sequences: dict, all_word_Xlengths: dict, this_word: str,
                 n_constant=3,
                 min_n_components=2, max_n_components=10,
                 random_state=14, verbose=False):
        self.words = all_word_sequences
        self.hwords = all_word_Xlengths
        self.sequences = all_word_sequences[this_word]
        self.X, self.lengths = all_word_Xlengths[this_word]
        self.this_word = this_word
        self.n_constant = n_constant
        self.min_n_components = min_n_components
        self.max_n_components = max_n_components
        self.random_state = random_state
        self.verbose = verbose

    def select(self):
        raise NotImplementedError

    def base_model(self, num_states):
        # with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            hmm_model = GaussianHMM(n_components=num_states, covariance_type="diag", n_iter=1000,
                                    random_state=self.random_state, verbose=False).fit(self.X, self.lengths)
            if self.verbose:
                print("model created for {} with {} states".format(self.this_word, num_states))
            return hmm_model
        except:
            if self.verbose:
                print("failure on {} with {} states".format(self.this_word, num_states))
            return None


class SelectorConstant(ModelSelector):
    """ select the model with value self.n_constant

    """

    def select(self):
        """ select based on n_constant value

        :return: GaussianHMM object
        """
        best_num_components = self.n_constant
        return self.base_model(best_num_components)


class SelectorBIC(ModelSelector):
    """ select the model with the lowest Bayesian Information Criterion(BIC) score

    http://www2.imm.dtu.dk/courses/02433/doc/ch6_slides.pdf
    Bayesian information criteria: BIC = -2 * logL + p * logN
    """

    def select(self):
        """ select the best model for self.this_word based on
        BIC score for n between self.min_n_components and self.max_n_components

        :return: GaussianHMM object
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection based on BIC scores

        optimal_hmm_model = None
        num_of_features = self.X.shape[1]
        best_BIC = float("inf")
        logN = np.log(len((self.lengths)))

        for num_states in range(self.min_n_components, self.max_n_components + 1):
            try:
                hmm_model = self.base_model(num_states)
                log_likelihood = hmm_model.score(self.X, self.lengths)
                # number of parameters
                p = num_states + (num_states * (num_states - 1)) + (num_states * num_of_features * 2)

                # Calculate Bayesian Information Criteria (BIC)
                BIC_score = -2 * log_likelihood + p * logN
            except:
                continue

            # Select best model
            if best_BIC > BIC_score:
                optimal_hmm_model = hmm_model
                best_BIC = BIC_score

        return optimal_hmm_model


class SelectorDIC(ModelSelector):
    ''' select best model based on Discriminative Information Criterion

    Biem, Alain. "A model selection criterion for classification: Application to hmm topology optimization."
    Document Analysis and Recognition, 2003. Proceedings. Seventh International Conference on. IEEE, 2003.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.58.6208&rep=rep1&type=pdf
    https://pdfs.semanticscholar.org/ed3d/7c4a5f607201f3848d4c02dd9ba17c791fc2.pdf
    DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection based on DIC scores
        n_word = len((self.words).keys())
        optimal_hmm_model = None
        optimal_DIC = float('-inf')

        for num_states in range(self.min_n_components, self.max_n_components + 1):
            try:
                hmm_model = self.base_model(num_states)
                log_likelihood = hmm_model.score(self.X, self.lengths)
            except:
                log_likelihood = float("-inf")
            
            log_sum = 0

            for word in self.hwords.keys():
                ix_word, word_lengths = self.hwords[word]

            try:
                log_sum += hmm_model.score(ix_word, word_lengths)

            except:
                log_sum += 0


            # DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
            DIC_Score = log_likelihood - (1 / (n_word - 1)) * (log_sum - (0 if log_likelihood == float("-inf") else log_likelihood))

            # Select best model
            if DIC_Score > optimal_DIC:
                optimal_DIC = DIC_Score
                optimal_hmm_model = hmm_model

        return optimal_hmm_model


class SelectorCV(ModelSelector):
    ''' select best model based on average log Likelihood of cross-validation folds

    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection using CV
        optimal_cv_score = float('-inf')
        optimal_hmm_model = None

        # Check for appropriate data for KFold
        if len(self.sequences) < 2:
            return None

        kf = KFold(n_splits=2)

        for num_states in range(self.min_n_components, self.max_n_components + 1):
            log_sum = 0
            cnt = 0

            # Iterate sequences
            for cv_train_ix, cv_test_ix in kf.split(self.sequences):

                # Train and test using KFold
                X_train, lengths_train = combine_sequences(cv_train_ix, self.sequences)
                X_test, lengths_test = combine_sequences(cv_test_ix, self.sequences)

                try:
                     # Train GaussianHMM model
                    hmm_model = GaussianHMM(n_components=num_states, covariance_type="diag", n_iter=1000,
                                            random_state=self.random_state, verbose=False).fit(X_train, lengths_train)

                    log_likelihood = hmm_model.score(X_test, lengths_test)
                    cnt += 1

                except:
                    log_likelihood = 0

                log_sum += log_likelihood

            # Calculate Score
            cv_score = log_sum / (1 if cnt == 0 else cnt)

            # Select optimal model
            if cv_score > optimal_cv_score:
                optimal_cv_score = cv_score
                optimal_hmm_model = hmm_model

        return optimal_hmm_model
