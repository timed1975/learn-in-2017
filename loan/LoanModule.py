from collections import namedtuple
import os
import urllib.parse as URL
import xml.etree.ElementTree as TREE

def calc_monthly_payment(amt, rate, pymnts):
    mthly_rate = float(rate) / (12 * 100)
    period_calc = 1 - pow(1 + mthly_rate, -int(pymnts))
    return round(float(amt) * (mthly_rate / period_calc), 2)

class LoanException(Exception):
    def __init__(self, message):
        self.message = message

class LoanDate(object):
    the_months = (None, 'Jan', 'Feb',
                  'Mar', 'Apr', 'May',
                  'Jun', 'Jul', 'Aug',
                  'Sep', 'Oct', 'Nov',
                  'Dec')
    mos_per_yr = len(the_months) - 1
    MON, YR = range(2)

    @property
    def date_tup(self):
        return self.m, self.y

    def __init__(self, m, y):
        self.m = int(m)
        self.y = int(y)

    @classmethod
    def from_str(cls, date_str):
        date = date_str.split('-')
        mon = LoanDate.the_months.index(date[LoanDate.MON])
        yr = int(date[LoanDate.YR])
        return cls(mon, yr)

    def __str__(self):
        return "{:s}-{:d}".format(self.the_months[self.m], self.y)

    def __sub__(self, my):
        mos_elapsed = self.m - my.m + 1
        yrs_elapsed = (self.y - my.y) * self.mos_per_yr
        return mos_elapsed + yrs_elapsed - 1

    def add_to(self, m=0, y=0):
        added_mos = self.m + m - 1
        added_yrs = self.y + y + added_mos // self.mos_per_yr
        return LoanDate(added_mos % self.mos_per_yr + 1, added_yrs)

    def months_and_years_between(self, my):
        mos_elapsed = self.m - my.m + 1
        yrs_elapsed = ((self.y - my.y) * self.mos_per_yr) - mos_elapsed
        print(self.m, my.m)
        print(mos_elapsed)
        return mos_elapsed, yrs_elapsed

class LoanAttrBase(object):
    def __init__(self):
        self.value = None

    def set_from_preset(self, val):
        if val is not None:
            self.value = self.val_type(val)
            return True
        return False

    def set_from_attributes(self, **kwargs):
        attrs = list()
        for attr in self.required_attrs:
            if kwargs.get(attr) is None:
                err_msg = "missing required argument: '{0}'".format(attr)
                raise LoanException(err_msg)
            attrs.append(kwargs[attr])
        try:
            self.value = self.setter(*attrs)
        except AttributeError:
            err_msg = "setter function not implemented"
            raise LoanException(err_msg)

class LoanAttrName(LoanAttrBase):
    def set_from_preset(self, val):
        self.val_type = str
        return LoanAttrBase.set_from_preset(self, val)

    def set_from_attributes(self, **kwargs):
        self.required_attrs = ('name',)
        LoanAttrBase.set_from_attributes(self, **kwargs)

class LoanAttrAmt(LoanAttrBase):
    def set_from_preset(self, val):
        self.val_type = float
        return LoanAttrBase.set_from_preset(self, val)

    def set_from_attributes(self, **kwargs):
        self.required_attrs = ('mnthly_pymnt', 'rate', 'pymnts')
        LoanAttrBase.set_from_attributes(self, **kwargs)

class LoanAttrRate(LoanAttrBase):
    def set_from_preset(self, val):
        self.val_type = float
        return LoanAttrBase.set_from_preset(self, val)

    def set_from_attributes(self, **kwargs):
        self.required_attrs = ('amt', 'mnthly_pymnt', 'pymnts')
        LoanAttrBase.set_from_attributes(self, **kwargs)

class LoanAttrPymnts(LoanAttrBase):
    def set_from_preset(self, val):
        self.val_type = int
        return LoanAttrBase.set_from_preset(self, val)

    def set_from_attributes(self, **kwargs):
        self.required_attrs = ('amt', 'rate', 'mnthly_pymnt')
        LoanAttrBase.set_from_attributes(self, **kwargs)

class LoanAttrMnthlyPymnt(LoanAttrBase):
    def set_from_preset(self, val):
        self.val_type = float
        return LoanAttrBase.set_from_preset(self, val)

    def set_from_attributes(self, **kwargs):
        self.required_attrs = ('amt', 'rate', 'pymnts')
        self.setter = calc_monthly_payment
        LoanAttrBase.set_from_attributes(self, **kwargs)

class LoanAttrDate(LoanAttrBase):
    def set_from_preset(self, val):
        self.val_type = LoanDate.from_str
        return LoanAttrBase.set_from_preset(self, val)

    def set_from_attributes(self, **kwargs):
        self.required_attrs = ('mon', 'yr')
        self.setter = LoanDate
        LoanAttrBase.set_from_attributes(self, **kwargs)

class Loan(object):

    (P,                  # principal
     I,                  # interest
     TOTAL_I,            # total interest
     BAL) = range(4)     # remaining balance

    __attributes = {
        'name': LoanAttrName(),
        'amt': LoanAttrAmt(),
        'rate': LoanAttrRate(),
        'pymnts': LoanAttrPymnts(),
        'mnthly_pymnt': LoanAttrMnthlyPymnt(),
        'date': LoanAttrDate()
    }

    @property
    def name(self):
        return self.__attributes['name'].value
    @property
    def initial_balance(self):
        return self.__attributes['amt'].value
    @property
    def lifetime(self):
        return self.__attributes['pymnts'].value
    @property
    def interest_rate(self):
        return self.__attributes['rate'].value
    @property
    def monthly_payment(self):
        return self.__attributes['mnthly_pymnt'].value
    @property
    def origination_date(self):
        return str(self.__attributes['date'].value)
    @property
    def next_payment_date(self):
        return str(self.__next_pymnt_due)
    @property
    def core_attributes(self):
        return self.__attributes

    def __init__(self, *args, **kwargs):
        for tag, loan_attr in self.__attributes.items():
            if self.__attributes[tag].set_from_preset(kwargs.get(tag)) is False:
                self.__attributes[tag].set_from_attributes(**kwargs)
        self.__xtra_p_pymnts = list()
        self.__amortization = self.amortize()
        if kwargs.get('xtra_pymnts') is not None:
            self.__xtra_p_pymnts = \
                [ float(payment) for payment in kwargs['xtra_pymnts'] ]
        past_additionals = len(self.__xtra_p_pymnts)
        self.__next_pymnt_due = self.__attributes['date'].value.add_to(past_additionals)

    @classmethod
    def from_query(cls, query):
        query_map = URL.parse_qs(query)
        loan_data = { name: val[0] for name,val in query_map.items() }
        return cls(**loan_data)

    def __past_additionals(self):
        for amt in self.__xtra_p_pymnts:
            yield amt
        while True:
            yield -1

    def amortize(self, planned_a=0):
        """ generate a monthly payment schedule """
        interest_paid = 0
        # attributes
        balance = self.__attributes['amt'].value
        date = self.__attributes['date'].value
        monthly_rate = self.__attributes['rate'].value  / (12 * 100)
        monthly_payment = self.__attributes['mnthly_pymnt'].value
        # past_additonals generator
        past_a = self.__past_additionals()
        schedule = dict()
        # timing for amortize(): 0.0007479353907892902
        while balance > 0:
            # use the given additional payment or a past payment if one exists
            a = next(past_a)
            if (a < 0):
                a = planned_a
            # calculate interest and principal payments for the month
            i = balance * monthly_rate
            p = min(monthly_payment - i + a, balance)
            # calculate accumlated interest payment and new balance
            interest_paid += i
            balance -= p
            # store in monthly payment schedule
            schedule[str(date)] = (p, i, interest_paid, balance)
            date = date.add_to(1)
        return schedule

    def get_monthly_report(self, schedule, date):
        return schedule[date]

    def get_total_payments(self, schedule=None):
        if schedule is None:
            return self.__attributes['pymnts'].value
        return len(schedule)

    def get_final_payment_date(self, schedule=None):
        if schedule is None:
            tot_pymnts = self.get_total_payments()
        tot_pymnts = self.get_total_payments(schedule)
        return self.__attributes['date'].value.add_to(tot_pymnts - 1)

    def get_stats(self, schedule):
        if schedule == self.__amortization:
            return 0, self.get_final_payment_date(), 0, 0
        # compare last month's payment data to the same month's default data
        to_date = self.__next_pymnt_due.add_to(-1)
        amts = schedule[str(to_date)]
        defaults = self.__amortization[str(to_date)]
        saved_so_far = defaults[self.TOTAL_I] - amts[self.TOTAL_I]
        # compare the final payment date of the schedule to
        # the final payment date of the default schedule
        def_final_date = self.get_final_payment_date()
        est_final_date = self.get_final_payment_date(schedule)
        pymnts_voided = def_final_date - est_final_date
        # compare the final month's data to the data
        # from the default schedule's final month
        amts = schedule[str(est_final_date)]
        defaults = self.__amortization[str(def_final_date)]
        tot_i_saved = defaults[self.TOTAL_I] - amts[self.TOTAL_I]
        # stats tuple for the caller to use
        return saved_so_far, est_final_date, pymnts_voided, tot_i_saved

    def get_amts_due(self):
        schedule = self.amortize()
        p, i, i_paid, bal = schedule[str(self.__next_pymnt_due)]
        return p, i

    def get_history(self, identifier=None):
        schedule = self.amortize()
        pymnts_made = self.__next_pymnt_due - self.__attributes['date'].value
        pymnts_list = list(schedule.items())[:pymnts_made]
        history = { pymnt[0]: pymnt[1] for pymnt in pymnts_list }
        return history

    def dump(self):
        for tag, attr in self.__attributes.items():
            print(tag, attr.value)

class LoanDB(object):
    def __init__(self):
        self.__db_name = os.path.join(os.getcwd(), 'loan', '__data__', 'loan_data.xml')

    def exists(self):
        try:
            db_file = open(self.__db_name, 'r')
            db_file.close()
        except FileNotFoundError:
            return False
        return True

    def create(self):
        loans_level = TREE.Element('Loans')
        tree = TREE.ElementTree(loans_level)
        tree.write(self.__db_name, xml_declaration=True)

    def __find(self, loan_name):
        loans_level = TREE.parse(self.__db_name)
        loans = loans_level.findall('Loan')
        for element in loans:
            if element.findtext('name') == loan_name:
                return element
        return None

    def add(self, loan):
        ''' add the loan to the xml database; if the loan
            already exists in the database, do nothing '''
        if self.__find(loan.name) is not None:
            return
        tree = TREE.ElementTree(file=self.__db_name)
        loans_level = tree.getroot()
        loan_level = TREE.SubElement(loans_level, 'Loan')
        for (name, val) in loan.core_attributes.items():
            attr_level = TREE.SubElement(
                loan_level,
                name,
            )
            attr_level.text = str(val.value)
        addtnl_pymnts_level = TREE.SubElement(loan_level, 'xtra_pymnts')
        tree.write(self.__db_name, xml_declaration=True)

    def get(self, name):
        try:
            # get the xml loan data from the database
            loan_element = self.__find(name)
            # return a Loan object from the xml data
            loan_data = dict()
            for attr in loan_element.iter():
                if len(attr) == 0:
                    loan_data[attr.tag] = attr.text
                else:
                    loan_data[attr.tag] = [ item.text for item in list(attr) ]
        except:
            error_str = "'{:s}' not found in database".format(name)
            raise LoanException(error_str)
        return Loan(**loan_data)
