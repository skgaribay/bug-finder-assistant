def print_hyperlink(url, text):
    print("\033]8;;{}\033\\{}\033]8;;\033\\".format(url, text))

# Example usage:
url = "https://sourcefitdev.atlassian.net/browse/KM-1005"
text = "Click here to visit Example"
print_hyperlink(url, text)
