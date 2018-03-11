import http.server
import math

class SimpleDate:
    the_months = (None, 'Jan', 'Feb',
                  'Mar', 'Apr', 'May',
                  'Jun', 'Jul', 'Aug',
                  'Sep', 'Oct', 'Nov',
                  'Dec')
    mos_per_yr = len(the_months) - 1
    (MON, YR) = range(2)

    def __init__(self, m, y):
        self.m = m
        self.y = y

    def add_to(self, m=0, y=0):
        added_mos = self.m + m - 1
        added_yrs = self.y + y + added_mos // self.mos_per_yr
        return SimpleDate(added_mos % self.mos_per_yr + 1, added_yrs)

    def months_between(self, my):
        mos_elapsed = self.m - my.m + 1
        yrs_elapsed = (self.y - my.y) * self.mos_per_yr
        return mos_elapsed + yrs_elapsed - 1

    def months_and_years_between(self, my):
        mos_elapsed = self.m - my.m + 1
        yrs_elapsed = ((self.y - my.y) * self.mos_per_yr) - mos_elapsed
        print(self.m, my.m)
        print(mos_elapsed)
        return mos_elapsed, yrs_elapsed

    @property
    def date_str(self):
        return '{:s}-{:d}'.format(self.the_months[self.m], self.y)

    @property
    def date_tup(self):
        return self.m, self.y

class Loan:
    row_fmt = '{:s}-{:d}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}'
    html_row_fmt = '<tr>\n<td>{:s}-{:d}</td>\n<td>${:.2f}</td>\n<td>${:.2f}</td>\n<td>${:.2f}</td>\n<td>${:.2f}</td>\n<td>${:.2f}</td>\n</tr>\n'

    (P,                  # principal
     I,                  # interest
     TOTAL_I,            # total interest
     BAL) = range(4)     # remaining balance

    def __init__(self, amount, rate, payments, start, server_addr = ('localhost', 55124), server_class = http.server.HTTPServer):
        self.__loan_amount = amount
        self.__balance = amount
        self.__interest_rate = (rate / (12 * 100))
        self.__lifetime = payments
        mp_numer = self.__interest_rate
        mp_denom = 1 - math.pow(1 + self.__interest_rate, -self.__lifetime)
        self.__monthly_payment = round(amount * (mp_numer / mp_denom), 2)
        self.__total_cost = self.__monthly_payment * self.__lifetime
        self.__start_date = SimpleDate(start[SimpleDate.MON], start[SimpleDate.YR])
        self.__current_date = SimpleDate(start[SimpleDate.MON], start[SimpleDate.YR])
        self.__schedule_table = {}
        self.__additional_principal_payments = []

        loan = self

        class RequestHandler(http.server.BaseHTTPRequestHandler):

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()

                next_payment = loan.get_monthly_report('current-projected', loan.next_payment_date.date_tup)
                html_in = open("loan-print-templ.html", 'rb')
                html_out = b''
                for line in html_in:
                    if b'starting_balance' in line:
                        html_out += bytes('<td>Loan Amount</td>\n<td>${:.2f}</td>\n'.format(loan.starting_balance), 'utf-8')
                    elif b'interest_rate' in line:
                        html_out += bytes('<td>Interest Rate</td>\n<td>{:.2f}%</td>\n'.format(loan.interest_rate), 'utf-8')
                    elif b'total_payments' in line:
                        html_out += bytes('<td>Total Monthly Payments</td>\n<td>{:d}</td>\n'.format(loan.total_payments), 'utf-8')
                    elif b'monthly_payment' in line:
                        html_out += bytes('<td>Monthly Payment</td>\n<td>${:.2f}</td>\n'.format(loan.monthly_payment), 'utf-8')
                    elif b'total_cost' in line:
                        html_out += bytes('<td>Total Cost of Loan</td>\n<td>${:.2f}</td>\n'.format(loan.total_cost), 'utf-8')
                    elif b'next_payment_due' in line:
                        html_out += bytes('<td>Next Payment Due</td>\n<td>{:s}</td>\n'.format(loan.next_payment_date.date_str), 'utf-8')
                    elif b'next_payment_total' in line:
                        html_out += bytes('<td>Total Due</td>\n<td>${:.2f}</td>\n'.format(next_payment[Loan.P] + next_payment[Loan.I]), 'utf-8')
                    elif b'next_payment_p' in line:
                        html_out += bytes('<td>Principal Due</td>\n<td>${:.2f}</td>\n'.format(next_payment[Loan.P]), 'utf-8')
                    elif b'next_payment_int' in line:
                        html_out += bytes('<td>Principal Due</td>\n<td>${:.2f}</td>\n'.format(next_payment[Loan.I]), 'utf-8')
                    elif b'payment_history' in line:
                        schedule = loan.get_schedule()
                        for date, amounts in schedule:
                            row = loan.get_row_as_list(date, amounts)
                            html_out += bytes(Loan.html_row_fmt.format(row[0], row[1], row[2], row[3], row[4], row[5], row[6]), 'utf-8')
                    elif b'current_savings' in line:
                        to_date = loan.next_payment_date.add_to(-1)
                        default_amounts = loan.get_monthly_report('default', to_date.date_tup)
                        to_date_amounts = loan.get_monthly_report('current-projected', to_date.date_tup)
                        html_out += bytes('<td>Current Total Saved</td>\n<td>${:.2f}</td>\n'.format(default_amounts[Loan.TOTAL_I] - to_date_amounts[Loan.TOTAL_I]), 'utf-8')
                    elif b'projected_final_payment' in line:
                        final_payment_date = loan.get_final_payment_date('current-projected')
                        html_out += bytes('<td>Projected Final Payment</td>\n<td>{:s}</td>\n'.format(final_payment_date.date_str), 'utf-8')
                    elif b'ahead_of_schedule' in line:
                        saved_payments = loan.get_total_payments('default') - loan.get_total_payments('current-projected')
                        html_out += bytes('<td>Ahead of Schedule</td>\n<td>{:d} months</td>\n'.format(saved_payments), 'utf-8')
                    elif b'total_savings' in line:
                        payoff_date = loan.get_final_payment_date('default')
                        final_payment_date = loan.get_final_payment_date('current-projected')
                        payoff_amounts = loan.get_monthly_report('default', payoff_date.date_tup)
                        final_amounts = loan.get_monthly_report('current-projected', final_payment_date.date_tup)
                        html_out += bytes('<td>Projected Savings on Interest</td>\n<td>${:.2f}</td>\n'.format(payoff_amounts[Loan.TOTAL_I] - final_amounts[Loan.TOTAL_I]), 'utf-8')
                    else:
                        html_out += line
                self.wfile.write(html_out)

        self.report_server = server_class(server_addr, RequestHandler)

    @property
    def starting_balance(self):
        return self.__loan_amount

    @property
    def remaining_balance(self):
        return self.__balance

    @property
    def interest_rate(self):
        return self.__interest_rate * 12 * 100

    @property
    def total_payments(self):
        return self.__lifetime

    @property
    def monthly_payment(self):
        return self.__monthly_payment

    @property
    def total_cost(self):
        return self.__total_cost

    @property
    def start_date(self):
        return self.__start_date

    @property
    def next_payment_date(self):
        return self.__current_date

    @property
    def payment_schedules(self):
        return self.__schedule_table

    def __past_additionals(self):
        for amt in self.__additional_principal_payments:
            yield amt
        while True:
            yield -1

    def amortize(self, identifier, planned_a=0):
        """ generate a monthly payment schedule """
        interest_paid = 0
        balance = self.__loan_amount
        date = self.__start_date
        past_a = self.__past_additionals()
        payment_schedule = {}
        # timing for amortize(): 0.0007479353907892902
        while balance > 0:
            # use the given additional payment or a past payment if one exists
            a = next(past_a)
            if (a < 0):
                a = planned_a
            # calculate interest and principal payments for the month
            i = balance * self.__interest_rate
            p = min(self.__monthly_payment - i + a, balance)
            # calculate accumlated interest payment and new balance
            interest_paid += i
            balance -= p
            # store in monthly payment schedule
            payment_schedule[date.date_tup] = (p, i, interest_paid, balance)
            date = date.add_to(1)

        self.__schedule_table[identifier] = payment_schedule

    def make_payment(self, a=0):
        i = self.__balance * self.__interest_rate
        p = min(self.__monthly_payment - i + a, self.__balance)
        self.__additional_principal_payments.append(a)
        self.__balance -= p
        self.__current_date = self.__current_date.add_to(1)

    def get_row_as_list(self, date, amounts):
        if amounts == None:
            return
        row = [SimpleDate.the_months[date[SimpleDate.MON]]]
        row.append(date[SimpleDate.YR])
        row.append(sum(amounts[:2]))
        for amount in amounts:
            row.append(amount)
        return row

    def get_monthly_report(self, identifier, date):
        return self.__schedule_table[identifier].get(date)

    def get_total_payments(self, identifier):
        return len(self.__schedule_table[identifier])

    def get_final_payment_date(self, identifier):
        payments = self.get_total_payments(identifier)
        return self.__start_date.add_to(payments - 1)

    def get_schedule(self, identifier=None):
        # TODO: make more pythonic
        if identifier == None:
            identifier = 'history'
            entry_limit = self.__current_date.months_between(self.__start_date)
            schedule = list(self.__schedule_table['current-projected'].items())[0:entry_limit]
        else:
            schedule = list(self.__schedule_table[identifier].items())
        return schedule

    def report(self):
        self.report_server.handle_request()

def print_stats(loan, identifier):
    to_date = loan.next_payment_date.add_to(-1)
    default_amounts = loan.get_monthly_report('default', to_date.date_tup)
    to_date_amounts = loan.get_monthly_report(identifier, to_date.date_tup)
    payoff_date = loan.get_final_payment_date('default')
    final_payment_date = loan.get_final_payment_date(identifier)
    payoff_amounts = loan.get_monthly_report('default', payoff_date.date_tup)
    final_amounts = loan.get_monthly_report(identifier, final_payment_date.date_tup)
    saved_payments = loan.get_total_payments('default') - loan.get_total_payments(identifier)

    print('\n\'{:s}\' Payment Statistics:'.format(identifier))
    print('current total saved on interest is ${:.2f}'.format(default_amounts[Loan.TOTAL_I] - to_date_amounts[Loan.TOTAL_I]))
    print('projected final payment date in', final_payment_date.date_str)
    print('projected final payment date is {:d} months ahead of schedule'.format(saved_payments))
    print('projected savings on interest is ${:.2f}'.format(payoff_amounts[Loan.TOTAL_I] - final_amounts[Loan.TOTAL_I]))


 # TODO: read from stdin or file
eames_way = Loan(238832.00, 4.25, 360, (8, 2017))
additional_principal_payments = [0.00, 845.00, 841.00, 1174.91, 832.00, 1174.91, 1586.60, 1174.91]

print('Loan Amount: ${:.2f}'.format(eames_way.starting_balance))
print('Interest Rate: {:.2f}%'.format(eames_way.interest_rate))
print('Total Monthly Payments: {:d}'.format(eames_way.total_payments))
print('Monthly Payment: ${:.2f}'.format(eames_way.monthly_payment))
print('Total Cost of Loan: ${:.2f}'.format(eames_way.total_cost))

# timing
#from time import perf_counter
#start = perf_counter()
#for times in range(1000000):
#end = perf_counter()
#print('default amortize:', (end - start) / 1000000)

eames_way.amortize('default')

for payment in additional_principal_payments:
    eames_way.make_payment(payment)

eames_way.amortize('current-projected')

schedule = eames_way.get_schedule()
print('\n\'{:s}\' Payment Schedule:'.format('history'))
for date, amounts in schedule:
    row = eames_way.get_row_as_list(date, amounts)
    print(Loan.row_fmt.format(row[0], row[1], row[2], row[3], row[4], row[5], row[6]).expandtabs(14))
next_payment = eames_way.get_monthly_report('current-projected', eames_way.next_payment_date.date_tup)
print('\n${:.2f} due in {:s}'.format(next_payment[Loan.I] + next_payment[Loan.P], eames_way.next_payment_date.date_str))
print('principal and interest amounts due are ${:.2f} and ${:.2f}'.format(next_payment[Loan.P], next_payment[Loan.I]))

print_stats(eames_way, 'current-projected')

eames_way.amortize('2035', 400.00)
print_stats(eames_way, '2035')

eames_way.amortize('$2000', 825.09)
print_stats(eames_way, '$2000')

eames_way.amortize('double', 1174.91)
print_stats(eames_way, 'double')

eames_way.amortize('original_int', 845.56)
print_stats(eames_way, 'original_int')

eames_way.amortize('total', eames_way.remaining_balance)
print_stats(eames_way, 'total')

eames_way.report()

quit()

while True:
    try:
        additional_for_month = input('Additional Monthly Payment: ')
        if 'PRINCIPAL'.startswith(additional_for_month.upper()):
            additional_for_month = 'PRINCIPAL'
            break
        elif 'INTEREST'.startswith(additional_for_month.upper()):
            additional_for_month = 'INTEREST'
            break
        else:
            additional_for_month = float(additional_for_month)
            break
    except ValueError:
        print('Error: invalid input')

try:
    out_file = open('EamesWayLoan.txt', 'w')
    writes_ok = True
except:
    print('Warning: output file not created')
    writes_ok = False
