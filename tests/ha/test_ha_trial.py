import pytest

class TestHATrial:
    def setup_class(self):
        #runs onces for a class
        print("Setup class")

    def setup_method(self):
        #run everytime test is called
        print("Setup method")

    def teardown_method(self):
        # everytime after the test
        print("teadwon method")

    def teardown_class(self):
        print("Teardown class")

    def test_1(self):
        "Randowm ts"
        print("Running test")
        assert True
        print("test completed")
