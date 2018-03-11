import LoanModule
from sys import argv
import subprocess

def main():
    loan_db = LoanModule.LoanDB()
    if loan_db.exists() is False:
        loan_db.create()

    try:
        target = argv[1]
        query = argv[2]
        if target is not "":
            err_msg = "do some stuff for {0} {1}".format(target, query)
            raise LoanModule.LoanException(err_msg)

        new_loan = LoanModule.Loan.from_query(query)
        loan_db.add(new_loan)
        results = subprocess.run(['python', 'loan/showloan.py', new_loan.name], stdout=subprocess.PIPE)
        print(results.stdout)

    except LoanModule.LoanException as err_msg:
        print(err_msg)

if __name__ == "__main__":
    main()
