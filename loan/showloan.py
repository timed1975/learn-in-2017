import LoanModule
import os
from sys import argv

attributes_table = "\
    <tr>  <td>Origination Date</td>  <td>{:s}</td>     </tr>\
    <tr>  <td>Amount</td>            <td>${:.2f}</td>  </tr>\
    <tr>  <td>Interest Rate</td>     <td>{:.2f}%</td>  </tr>\
    <tr>  <td>Lifetime</td>          <td>{:d}</td>     </tr>\
    <tr>  <td>Monthly Payment</td>   <td>${:.2f}</td>  </tr>\
"
payment_form = "\
    <form action=\"{:s}\" method=\"POST\">\
        <input type=\"text\" name=\"pymnt\">\
        <input type=\"submit\" value=\"Submit Payment\">\
    </form>\
"
amount_due_table = "\
    <tr>  <td>Next Payment Due</td>  <td>{:s}</td>     </tr>\
    <tr>  <td>Principal Due</td>     <td>${:.2f}</td>  </tr>\
    <tr>  <td>Interest Due</td>      <td>${:.2f}</td>  </tr>\
    <tr>  <td>Total Due</td>         <td>{:.2f}</td>  </tr>\
"
table_row = "\
    <tr>\
        <td>{:s}</td>\
        <td>${:.2f}</td>\
        <td>${:.2f}</td>\
        <td>${:.2f}</td>\
        <td>${:.2f}</td>\
        <td>${:.2f}</td>\
    </tr>\
"
stats_table = "\
    <tr>\
        <td>Total Saved on Interest (to-date)</td>\
        <td>${:.2f}</td>\
    </tr>\
    <tr>\
        <td>Estimated Final Payment Date</td>\
        <td>{:s}</td>\
    </tr>\
    <tr>\
        <td>Payments Avoided</td>\
        <td>{:d}</td>\
    </tr>\
    <tr>\
        <td>Estimated Total Saved on Interest</td>\
        <td>${:.2f}</td>\
    </tr>\
"

def main():
    try:
        loan_db = LoanModule.LoanDB()

        name = argv[1]
        current_loan = loan_db.get(name)

        attr_out = attributes_table.format(
            current_loan.origination_date,
            current_loan.initial_balance,
            current_loan.interest_rate,
            current_loan.lifetime,
            current_loan.monthly_payment
        )
        due_date = current_loan.next_payment_date
        principal_due, interest_due = current_loan.get_amts_due()
        due_out = amount_due_table.format(
            due_date,
            principal_due,
            interest_due,
            principal_due + interest_due,
        )
        history = current_loan.get_history()
        history_out = str()
        for date, amounts in history.items():
            row = [str(date)]
            row.append(sum(amounts[:2]))
            for amount in amounts:
                row.append(amount)
            history_out += table_row.format(*row)
        est_payoff_sched = current_loan.amortize()
        i_saved, est_final_date, payments_avoided, tot_i_saved = \
            current_loan.get_stats(est_payoff_sched)
        stats_out = stats_table.format(
            i_saved,
            str(est_final_date),
            payments_avoided,
            tot_i_saved
        )
        payment_submit_out = payment_form.format(current_loan.name)
        template_path = os.path.join(os.getcwd(), 'loan', '__html__', 'show_template.html')
        template = open(template_path)
        html_out = template.read()
        print(html_out.format(current_loan.name, attr_out, due_out, payment_submit_out, history_out, stats_out))
    except LoanModule.LoanException as err_msg:
        print(err_msg)

if __name__ == "__main__":
    main()
